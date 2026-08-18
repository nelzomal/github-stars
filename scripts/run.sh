#!/usr/bin/env bash
# Rebuild data/ and index.html from scratch.
#
# Steps 2, 3 and 5 talk to the GitHub API and need `gh auth login` done first;
# step 2 makes ~37k repository lookups and is the slow one (tens of minutes).
# It checkpoints to data/survival_*.jsonl, so re-running resumes rather than
# starting over; step 3 checkpoints to data/accounts_*.json the same way.
# Steps 4-6 are minutes.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p ../data

python3 1_reference.py      # -> data/reference.json      StarScout artifact, recomputed
python3 2_survival.py       # -> data/survival.json       which flagged repos still exist
python3 3_accounts.py       # -> data/accounts.json       which flagged *accounts* still exist
python3 4_blackout.py       # -> data/blackout.json       GH Archive decay + live endpoints
python3 5_trending_now.py   # -> data/trending_now.json   today's trending x surviving signals
python3 6_trending_hist.py  # -> data/trending_hist.json  trending archive cross-reference
python3 7_build.py          # -> data/site_data.json
python3 8_render.py         # -> index.html

echo
echo "done — open index.html"
