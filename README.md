# Big Matches Calendar (PL, LaLiga, UCL)

Generates a single `.ics` you can subscribe to in Google Calendar with
only the “big” head-to-head matches:

- **Premier League**: Chelsea, Arsenal, Manchester United, Manchester City, Tottenham Hotspur, Liverpool
- **La Liga**: FC Barcelona, Real Madrid, Atletico Madrid
- **Champions League**: the nine above + Bayern Munich

## How it works
- You provide official subscription URLs (ICS) in `sources.yaml`.
- A scheduled GitHub Action fetches all feeds daily, merges, classifies the competition, normalises team names (e.g., “Man Utd” → “Manchester United”, “Barça” → “FC Barcelona”), and **keeps only** matches where **both** teams belong to the target set for that competition.
- Output is `big_matches.ics` in the repo root.

## Setup
1. Get subscription URLs:
   - Premier League: use the official PL “Download fixtures to your calendar” flow (ECAL).
   - LaLiga: use the official LaLiga calendar sync flow (ECAL).
   - Champions League: add a per-team UCL feed for each relevant team, or a trusted aggregate UCL feed.
2. Paste them into `sources.yaml`.
3. Push to GitHub.

## Auto-updates & hosting
- GitHub Actions rebuilds daily.
- Enable **GitHub Pages → Deploy from Branch → `main` → `/` (root)**.
- Your ICS will be at:
  `https://<username>.github.io/<repo>/big_matches.ics`

## Subscribe in Google Calendar
- Google Calendar → “Other calendars” → “From URL” → paste the link above.
- It will auto-refresh on Google’s schedule.
