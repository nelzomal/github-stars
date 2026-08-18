#!/usr/bin/env bash
# Rebuild data/ and index.html from scratch.
#
# Steps 2 and 4 talk to the GitHub API and need `gh auth login` done first;
# step 2 makes ~37k repository lookups and is the slow one (tens of minutes).
# It checkpoints to data/survival_*.jsonl, so re-running resumes rather than
# starting over. Steps 3-5 are minutes.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p ../data

python3 1_reference.py      # -> data/reference.json      StarScout artifact, recomputed
python3 2_survival.py       # -> data/survival.json       which flagged repos still exist
python3 3_blackout.py       # -> data/blackout.json       GH Archive decay + live endpoints
python3 4_trending_now.py   # -> data/trending_now.json   today's trending x surviving signals
python3 5_trending_hist.py  # -> data/trending_hist.json  trending archive cross-reference
python3 6_build.py          # -> data/site_data.json
python3 7_render.py         # -> index.html

echo
echo "done — open index.html"
