"""Cross the flagged repositories against the GitHub Trending archive.

The paper reports that 78 of the 18,617 repos with a fake-star campaign turned
up on github.com/trending -- 0.42% of the *flagged* set. That is not the number
anyone actually wants, which is the other direction: of the repos that reached
Trending, how many were being faked? This computes both, per month, from the
community archive at github.com/larsbijl/trending_archive.

The archive follows six language boards (python, javascript, typescript, go,
rust, cpp) and not the all-languages front page, so its monthly repo count is a
subset of everything that trended. Coverage is written out per month rather
than described, so the caveat can be checked.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import json, re, subprocess, sys
from collections import defaultdict

REPO = "https://github.com/larsbijl/trending_archive.git"
CLONE = Path(D + "trending_archive")

if not CLONE.exists():
    print("cloning trending archive...", file=sys.stderr)
    subprocess.run(["git", "clone", "--depth", "1", "-q", REPO, str(CLONE)], check=True)
else:
    subprocess.run(["git", "-C", str(CLONE), "pull", "-q"], check=False)

LANG = re.compile(r"^#### (.+?)\s*$")
ITEM = re.compile(r"^\* \[([\w.-]+/[\w.-]+)\]")
DAY = re.compile(r"(\d{4})-(\d{2})-(\d{2})\.md$")

# day -> {repo -> set(languages)}; the *_short.md files repeat the same repos.
by_day = {}
for path in sorted(CLONE.rglob("*.md")):
    m = DAY.search(path.name)
    if not m:
        continue
    y, mo, d = m.groups()
    lang, entries = None, defaultdict(set)
    for line in path.read_text(errors="replace").splitlines():
        lm = LANG.match(line)
        if lm:
            lang = lm.group(1).strip().lower()
            continue
        im = ITEM.match(line)
        if im and lang:
            entries[im.group(1)].add(lang)
    if entries:
        by_day[f"{y}-{mo}-{d}"] = entries

print(f"{len(by_day)} days of trending archive, "
      f"{min(by_day)} to {max(by_day)}", file=sys.stderr)

ref = json.load(open(D + "reference.json"))
campaign = {r["repo"]: r for r in ref["repos"]}
# Case-insensitive, because the archive and GH Archive disagree on casing.
campaign_ci = {r.lower(): r for r in campaign}

by_month = defaultdict(lambda: {"repos": set(), "flagged": set(), "langs": set(), "days": 0})
first_seen = {}
for day, entries in by_day.items():
    month = day[:7]
    b = by_month[month]
    b["days"] += 1
    for repo, langs in entries.items():
        b["repos"].add(repo)
        b["langs"] |= langs
        hit = campaign_ci.get(repo.lower())
        if hit:
            b["flagged"].add(hit)
            first_seen.setdefault(hit, day)

series = [{
    "month": m,
    "days": b["days"],
    "trending_repos": len(b["repos"]),
    "flagged_repos": len(b["flagged"]),
    "p_flagged": len(b["flagged"]) / len(b["repos"]) if b["repos"] else None,
    "languages": sorted(b["langs"]),
} for m, b in sorted(by_month.items())]

matched = sorted(first_seen)
window = ref["source"]["window"]
in_window = [r for r in matched if window[0] <= first_seen[r][:7] <= window[1]]

out = {
    "archive": {"days": len(by_day), "from": min(by_day), "to": max(by_day),
                "repo": "github.com/larsbijl/trending_archive"},
    "series": series,
    "matched": [{
        "repo": r, "first_trending": first_seen[r],
        "n_stars": campaign[r]["n_stars"], "n_fake": campaign[r]["n_fake"],
        "p_fake": campaign[r]["p_fake"], "domain": campaign[r]["domain"],
    } for r in matched],
    "totals": {
        "campaign_repos": len(campaign),
        "ever_trending": len(matched),
        "ever_trending_in_paper_window": len(in_window),
        "p_of_campaign": len(matched) / len(campaign),
    },
}
json.dump(out, open(D + "trending_hist.json", "w"))

t = out["totals"]
print(f"campaign repos that ever trended: {t['ever_trending']} / {t['campaign_repos']} "
      f"= {t['p_of_campaign']:.2%}", file=sys.stderr)
print(f"  (within the detector's window {window[0]}..{window[1]}: "
      f"{t['ever_trending_in_paper_window']})", file=sys.stderr)
print("\nthe other direction -- share of trending repos that were being faked:",
      file=sys.stderr)
for s in series:
    if s["month"] >= "2023-01" and s["flagged_repos"]:
        print(f"  {s['month']}  {s['flagged_repos']:3d} / {s['trending_repos']:4d} "
              f"= {s['p_flagged']:5.2%}  ({','.join(s['languages'])})", file=sys.stderr)
