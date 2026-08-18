"""Pull the StarScout replication package and re-derive its repo/month tables.

Source: github.com/hehao98/StarScout, the artifact for He et al., "Six Million
(Suspected) Fake Stars on GitHub", ICSE'26 (doi 10.1145/3744916.3764531).
The CSVs under data/ there are cached exports of the detector's MongoDB, so the
whole thing works standalone -- no BigQuery, no Mongo, no 49 GB of GH Archive.

Everything below re-implements scripts/analysis/data.py from that repo in the
stdlib, so the definitions live in this file where a reader can check them
rather than in a pandas call somewhere else.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import csv, gzip, io, json, ssl, sys, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

RAW = "https://raw.githubusercontent.com/hehao98/StarScout/main/"
RUNS = ["240701", "241001", "250101"]  # the three detector cutoffs
CTX = ssl.create_default_context()

FILES = [f"data/{r}/fake_stars_{k}_{w}.csv"
         for r in RUNS
         for k in ("low_activity", "clustered")
         for w in ("repos", "stars_by_month")] + [
    "data/repo_labels.csv",
    "data/all_github_stars_by_month.csv",
    "data/all_github_users_by_month.csv",
    "data/all_github_repos_with_spikes.csv",
    "data/241001/sample_repo_ids.csv",  # the paper's random control group
]


def fetch(rel: str) -> str:
    """Download one artifact file into data/starscout/, cached on disk."""
    out = Path(D + "starscout/" + rel[len("data/"):])
    if out.exists() and out.stat().st_size > 0:
        return str(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(RAW + rel, headers={"User-Agent": "github-stars/1.0"})
    with urllib.request.urlopen(req, context=CTX, timeout=300) as r:
        body = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        body = gzip.decompress(body)
    out.write_bytes(body)
    print(f"  {rel}  {len(body)/1e6:.1f} MB", file=sys.stderr)
    return str(out)


def rows(path):
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def f2(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


print("fetching StarScout artifact...", file=sys.stderr)
with ThreadPoolExecutor(8) as ex:
    paths = dict(zip(FILES, ex.map(fetch, FILES)))

# ---------------------------------------------------------------- repo totals
# One row per repo per run; later runs supersede earlier ones (keep="last").
# n_stars is the sum across both signatures, matching get_fake_star_repos().
repos: dict[str, dict] = {}
for run in RUNS:
    merged: dict[str, dict] = {}
    for kind in ("low_activity", "clustered"):
        for r in rows(paths[f"data/{run}/fake_stars_{kind}_repos.csv"]):
            e = merged.setdefault(r["repo_name"], {"repo": r["repo_name"], "n_stars": 0.0,
                                                   "low_activity": 0.0, "clustered": 0.0})
            e["n_stars"] += f2(r["n_stars"])
            e[kind] += f2(r[f"n_stars_{kind}"])
    for name, e in merged.items():
        n = e["n_stars"] or 1.0
        e["p_fake"] = (e["low_activity"] + e["clustered"]) / n
        e["run"] = run
        repos[name] = e

# ------------------------------------------------------- monthly star tables
# (repo, month) -> real/fake split. Same supersede rule as above.
by_month: dict[tuple, dict] = {}
for run in RUNS:
    merged: dict[tuple, dict] = {}
    for kind in ("low_activity", "clustered"):
        for r in rows(paths[f"data/{run}/fake_stars_{kind}_stars_by_month.csv"]):
            k = (r["repo"], r["month"])
            e = merged.setdefault(k, {"n_stars": 0.0, "low_activity": 0.0, "clustered": 0.0})
            e["n_stars"] += f2(r["n_stars"])
            e[kind] += f2(r[f"n_stars_{kind}"])
    by_month.update(merged)

# A month is anomalous when >=50 fake stars land in it AND they are the
# majority of that month's stars. 50 is the merchants' usual minimum order.
for k, e in by_month.items():
    e["n_fake"] = e["low_activity"] + e["clustered"]
    e["anomaly"] = e["n_fake"] >= 50 and e["n_fake"] >= 0.5 * e["n_stars"]

anomalous_repos = {repo for (repo, _), e in by_month.items() if e["anomaly"]}

# A repo has a *campaign* (rather than a few stray fake stars) when at least
# 10% of its stars are fake and at least one month is anomalous.
campaign = {r for r, e in repos.items() if e["p_fake"] >= 0.1} & anomalous_repos

# ------------------------------------------------------------- monthly series
months = sorted({m for _, m in by_month})

# The final run cut off on 250101, so a few hours of events carry a 2025-01
# stamp -- 2,807 fake stars against ~320k in every full month before it. The
# rows stay (dropping them would move the repo count off the paper's 18,617),
# but the window is labelled by the last month actually observed end to end.
CUTOFF = "20%s-%s" % (RUNS[-1][:2], RUNS[-1][2:4])  # "250101" -> "2025-01"
full_months = [m for m in months if m < CUTOFF]
all_stars = {r["month"]: int(r["n_stars"]) for r in rows(paths["data/all_github_stars_by_month.csv"])}
all_users = {r["month"]: int(r["n_active_users"]) for r in rows(paths["data/all_github_users_by_month.csv"])}

popular_per_month: dict[str, int] = defaultdict(int)  # repos with >=50 stars that month
for r in rows(paths["data/all_github_repos_with_spikes.csv"]):
    popular_per_month[r["month"]] += 1

fake_stars_m, anom_repos_m = defaultdict(float), defaultdict(int)
for (repo, month), e in by_month.items():
    fake_stars_m[month] += e["n_fake"]
    if e["anomaly"]:
        anom_repos_m[month] += 1

series = [{
    "month": m,
    "fake_stars": round(fake_stars_m.get(m, 0)),
    "all_stars": all_stars.get(m),
    "anomalous_repos": anom_repos_m.get(m, 0),
    "popular_repos": popular_per_month.get(m),
    "p_repos": (anom_repos_m.get(m, 0) / popular_per_month[m]) if popular_per_month.get(m) else None,
    "p_stars": (fake_stars_m.get(m, 0) / all_stars[m]) if all_stars.get(m) else None,
} for m in months]

# --------------------------------------------------------------- manual codes
# 580 repos hand-coded by the paper's authors; `trending` marks the ones that
# reached github.com/trending, `domain` is the nine-way category.
labels = {r["repo"]: r for r in rows(paths["data/repo_labels.csv"])}

out = {
    "source": {
        "artifact": "github.com/hehao98/StarScout",
        "paper": "He et al., Six Million (Suspected) Fake Stars on GitHub, ICSE'26",
        "doi": "10.1145/3744916.3764531",
        "runs": RUNS,
        "window": [full_months[0], full_months[-1]],
        "raw_window": [months[0], months[-1]],
    },
    "totals": {
        "repos_flagged": len(repos),
        "repos_with_campaign": len(campaign),
        # Two different totals, both of which the paper quotes: every suspected
        # fake star anywhere (its "six million"), and the subset landing in
        # repos that clear the campaign bar (its 3.81M). Summing the per-repo
        # rows instead would double-count nothing but silently drop the months
        # a repo was flagged in an earlier run, so both come from by_month.
        "fake_stars": round(sum(fake_stars_m.values())),
        "fake_stars_in_campaigns": round(
            sum(e["n_fake"] for (r, _), e in by_month.items() if r in campaign)),
        "labelled": len(labels),
        "labelled_trending": sum(1 for r in labels.values() if r["trending"] == "True"),
    },
    "series": series,
    "repos": [{
        "repo": r,
        "n_stars": round(repos[r]["n_stars"]),
        "n_fake": round(repos[r]["low_activity"] + repos[r]["clustered"]),
        "p_fake": round(repos[r]["p_fake"], 4),
        "low_activity": round(repos[r]["low_activity"]),
        "clustered": round(repos[r]["clustered"]),
        "domain": labels.get(r, {}).get("domain"),
        "trending": labels.get(r, {}).get("trending") == "True",
        "packages": labels.get(r, {}).get("packages") == "True",
    } for r in sorted(campaign)],
    "by_month": [{
        "repo": repo, "month": month,
        "n_stars": round(e["n_stars"]), "n_fake": round(e["n_fake"]),
        "anomaly": e["anomaly"],
    } for (repo, month), e in sorted(by_month.items()) if repo in campaign],
}

json.dump(out, open(D + "reference.json", "w"))
print(f"flagged repos      {out['totals']['repos_flagged']}", file=sys.stderr)
print(f"with campaign      {out['totals']['repos_with_campaign']}", file=sys.stderr)
print(f"suspected fake     {out['totals']['fake_stars']:,}   论文 ~6.0M", file=sys.stderr)
print(f"  in campaigns     {out['totals']['fake_stars_in_campaigns']:,}   论文 3.81M", file=sys.stderr)
print(f"hand-coded         {out['totals']['labelled']} ({out['totals']['labelled_trending']} trending)", file=sys.stderr)
peak = max(series, key=lambda s: s["p_repos"] or 0)
print(f"peak repo share    {peak['month']}  {peak['p_repos']:.2%}  ({peak['anomalous_repos']}/{peak['popular_repos']})", file=sys.stderr)
