#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

import requests
import yaml
from ics import Calendar

# ---------- Config & constants ----------

THIS_DIR = Path(__file__).parent
OUT_PATH = THIS_DIR / "big_matches.ics"

# Competition keys expected in sources.yaml
COMP_PL = "Premier League"
COMP_LL = "La Liga"
COMP_UCL = "Champions League"

# Canonical team sets per competition (exact canonical names)
PL_BIG = {
    "Chelsea", "Arsenal", "Manchester United", "Manchester City",
    "Tottenham Hotspur", "Liverpool"
}
LL_BIG = {"FC Barcelona", "Real Madrid", "Atletico Madrid"}
UCL_BIG = {
    "FC Barcelona", "Real Madrid", "Atletico Madrid",
    "Chelsea", "Arsenal", "Manchester United", "Manchester City",
    "Tottenham Hotspur", "Liverpool", "Bayern Munich"
}

CANON_BY_COMP = {
    COMP_PL: PL_BIG,
    COMP_LL: LL_BIG,
    COMP_UCL: UCL_BIG,
}

# Name normalisation map -> canonical
# Add common abbreviations & unicode variants
NORMALISE = {
    # Premier League big six
    "chelsea": "Chelsea",
    "arsenal": "Arsenal",
    "manchester united": "Manchester United",
    "manchester utd": "Manchester United",
    "man utd": "Manchester United",
    "man u": "Manchester United",
    "manchester city": "Manchester City",
    "man city": "Manchester City",
    "tottenham hotspur": "Tottenham Hotspur",
    "tottenham": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "liverpool": "Liverpool",

    # La Liga trio
    "fc barcelona": "FC Barcelona",
    "barcelona": "FC Barcelona",
    "barça": "FC Barcelona",
    "barca": "FC Barcelona",
    "real madrid": "Real Madrid",
    "atlético madrid": "Atletico Madrid",
    "atletico madrid": "Atletico Madrid",
    "atlético de madrid": "Atletico Madrid",

    # UCL extra
    "bayern munich": "Bayern Munich",
    "fc bayern": "Bayern Munich",
    "bayern münchen": "Bayern Munich",
}

TEAM_SPLIT_REGEX = re.compile(r"\b(?:vs\.?|v\.?|–|-|—|:)\b", re.IGNORECASE)

def _slug(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()

def normalise_team(name: str) -> str:
    n = _slug(name)
    # remove extra descriptors like "(Men)", "(First Team)"
    n = re.sub(r"\(.*?\)", "", n).strip()
    return NORMALISE.get(n, name.strip())

def extract_teams(title: str):
    """
    Try to split an event title into home/away teams.
    Handles patterns like:
      "Liverpool v Chelsea"
      "Chelsea vs Liverpool"
      "Chelsea - Liverpool"
      "Liverpool — Chelsea"
      "Liverpool: Chelsea"
    Returns (team1, team2) or (None, None)
    """
    if not title:
        return None, None
    parts = TEAM_SPLIT_REGEX.split(title)
    if len(parts) >= 2:
        t1 = normalise_team(parts[0])
        t2 = normalise_team(parts[1])
        return t1, t2
    return None, None

def guess_competition(event):
    """
    Try to infer competition from event fields.
    Priority: categories -> description -> location -> title
    """
    haystacks = []
    # ics.Event fields are not guaranteed; guard with getattr
    title = getattr(event, "name", "") or ""
    description = getattr(event, "description", "") or ""
    location = getattr(event, "location", "") or ""

    # Some feeds include categories in description text
    haystacks.extend([title, description, location])

    text = " ".join([h for h in haystacks if h]).lower()

    if "premier league" in text or "epl" in text:
        return COMP_PL
    if "la liga" in text or "laliga" in text or "la liga ea sports" in text:
        return COMP_LL
    if "champions league" in text or "uefa champions league" in text or "ucl" in text:
        return COMP_UCL

    # Unknown -> None; caller may supply default by source
    return None

def fetch_calendar(url: str) -> Calendar:
    # Support webcal:// by converting to https://
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Calendar(r.text)

def event_uid(event) -> str:
    # Preserve existing UID if present; otherwise derive a stable one
    uid = getattr(event, "uid", None)
    if uid:
        return uid
    base = f"{getattr(event,'name','')}|{getattr(event,'begin','')}|{getattr(event,'location','')}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest() + "@bigmatches"

def main():
    # Load sources
    src_path = THIS_DIR / "sources.yaml"
    if not src_path.exists():
        print("Missing sources.yaml. See README.md.", file=sys.stderr)
        sys.exit(1)

    sources = yaml.safe_load(src_path.read_text(encoding="utf-8"))
    # Expected: { "Premier League": [url1, url2, ...], "La Liga": [...], "Champions League": [...] }

    merged = Calendar()
    merged.extra.append(("X-WR-CALNAME", "Big Matches (PL, LaLiga, UCL)"))
    merged.extra.append(("X-WR-TIMEZONE", "UTC"))  # keep as-is; events carry their own times

    total_in, total_kept = 0, 0

    for comp_key, urls in (sources or {}).items():
        if not urls:
            continue

        for url in urls:
            try:
                cal = fetch_calendar(url)
            except Exception as e:
                print(f"[warn] Failed to fetch {comp_key} feed {url}: {e}", file=sys.stderr)
                continue

            for ev in cal.events:
                total_in += 1

                # Determine competition: explicit by config key or best guess by content
                comp = comp_key if comp_key in CANON_BY_COMP else guess_competition(ev)
                if comp not in CANON_BY_COMP:
                    # If we still can't classify, skip
                    continue

                t1, t2 = extract_teams(getattr(ev, "name", ""))
                if not t1 or not t2:
                    # Sometimes team names appear only in description
                    t1, t2 = extract_teams(getattr(ev, "description", ""))

                if not t1 or not t2:
                    continue  # cannot evaluate

                canon_set = CANON_BY_COMP[comp]
                if t1 in canon_set and t2 in canon_set:
                    # Ensure stable UID
                    ev.uid = event_uid(ev)
                    merged.events.add(ev)
                    total_kept += 1

    # Write output ICS
    OUT_PATH.write_text("\n".join(merged.serialize_iter()), encoding="utf-8")
    print(json.dumps({"events_in": total_in, "events_kept": total_kept, "out": str(OUT_PATH)}))

if __name__ == "__main__":
    main()
