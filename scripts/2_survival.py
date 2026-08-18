"""Ask GitHub, today, which of the flagged repositories still exist.

The paper checked this once in January 2025. This re-runs the check at whatever
today's date is, against a month-matched control group built below, because the
gap between the two is the only external evidence that the detector was
pointing at something real rather than at noise.

GraphQL, 100 repositories per request via aliases, cost 1 point each.
A deleted repo comes back as a null field plus a NOT_FOUND entry in `errors`.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import json, ssl, subprocess, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.github.com/graphql"
BATCH = 100
CTX = ssl.create_default_context()
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                       check=True).stdout.strip()
if not TOKEN:
    sys.exit("no GitHub token: run `gh auth login` first")

FIELDS = ("nameWithOwner isArchived isFork isPrivate createdAt pushedAt "
          "stargazerCount forkCount")


def call(query: str, tries: int = 3) -> dict:
    body = json.dumps({"query": query}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-stars/1.0",
    })
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
                res = json.loads(r.read())
            if any(e.get("type") == "RATE_LIMITED" for e in (res.get("errors") or [])):
                wait_for_reset()
                continue
            return res
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                wait_for_reset(e.headers.get("x-ratelimit-reset"))
                continue
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("retries exhausted")


_reset_lock = __import__("threading").Lock()


def wait_for_reset(header=None):
    """Sleep until the GraphQL budget refills. One thread waits, the rest queue
    behind the lock and find the budget already restored."""
    with _reset_lock:
        try:
            out = subprocess.run(["gh", "api", "rate_limit", "--jq",
                                  ".resources.graphql | [.remaining, .reset] | @tsv"],
                                 capture_output=True, text=True, timeout=60).stdout.split()
            remaining, reset = int(out[0]), int(out[1])
        except Exception:
            remaining, reset = 0, int(float(header or 0)) or int(time.time()) + 60
        if remaining > 50:
            return
        delay = max(reset - int(time.time()), 0) + 5
        print(f"  rate limited; sleeping {delay}s until "
              f"{time.strftime('%H:%M:%S', time.localtime(reset))}", file=sys.stderr)
        time.sleep(delay)


def probe(batch: list[str]) -> list[dict]:
    """Probe a batch, halving it if the server refuses the whole thing.

    A handful of repos are expensive enough (hundreds of thousands of commits,
    thousands of contributors) that a 100-alias query times out and GitHub
    answers 502. Splitting isolates them instead of losing the batch.
    """
    try:
        return probe_once(batch)
    except Exception as e:
        if len(batch) == 1:
            print(f"  giving up on {batch[0]}: {e}", file=sys.stderr)
            return [{"repo": batch[0], "alive": None, "error": str(e)[:200]}]
        mid = len(batch) // 2
        return probe(batch[:mid]) + probe(batch[mid:])


def probe_once(batch: list[str]) -> list[dict]:
    """One request for up to BATCH repos. Returns a record per input repo."""
    parts = []
    for i, full in enumerate(batch):
        owner, _, name = full.partition("/")
        parts.append('r%d: repository(owner:%s, name:%s){%s}'
                     % (i, json.dumps(owner), json.dumps(name), FIELDS))
    res = call("{" + "\n".join(parts) + "}")
    data = res.get("data")
    # A missing `data` means the whole request failed (rate limit, timeout).
    # Recording that as "every repo in this batch is deleted" would be silent
    # corruption of the one number this script exists to produce, so fail loud.
    if not isinstance(data, dict):
        raise RuntimeError(f"no data in response: {json.dumps(res)[:300]}")
    out = []
    for i, full in enumerate(batch):
        node = data.get(f"r{i}")
        if node is None:
            out.append({"repo": full, "alive": False})
            continue
        out.append({
            "repo": full, "alive": True,
            # A rename leaves the old name resolvable; record where it landed.
            "now": node["nameWithOwner"],
            "archived": node["isArchived"], "fork": node["isFork"],
            "created_at": node["createdAt"], "pushed_at": node["pushedAt"],
            "stars": node["stargazerCount"], "forks": node["forkCount"],
        })
    return out


def run(name: str, repos: list[str]) -> list[dict]:
    """Probe a list of repos, checkpointing so an interrupted run resumes."""
    ckpt = Path(D + f"survival_{name}.jsonl")
    done, kept = set(), []
    if ckpt.exists():
        with ckpt.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("alive") is None:
                    continue
                if rec["repo"] not in done:
                    done.add(rec["repo"])
                    kept.append(line.rstrip("\n"))
        ckpt.write_text("\n".join(kept) + ("\n" if kept else ""))
    todo = [r for r in repos if r not in done]
    print(f"{name}: {len(repos)} repos, {len(done)} cached, {len(todo)} to probe",
          file=sys.stderr)
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with ckpt.open("a") as f, ThreadPoolExecutor(4) as ex:
        for n, recs in enumerate(ex.map(probe, batches), 1):
            for rec in recs:
                f.write(json.dumps(rec) + "\n")
            f.flush()
            if n % 10 == 0 or n == len(batches):
                print(f"  {name} {n}/{len(batches)}", file=sys.stderr)
    with ckpt.open() as f:
        return [json.loads(line) for line in f if line.strip()]


ref = json.load(open(D + "reference.json"))
flagged = [r["repo"] for r in ref["repos"]]

# Control group, built here rather than taken from the artifact so its
# construction is inspectable. Drawn from the same population the flagged repos
# came from -- repos that got >=50 stars in some month, i.e. popular enough to
# be worth faking -- with every repo the detector touched removed.
#
# Matched on month: a repo that spiked in 2019 has had six more years to be
# deleted than one that spiked in 2024, and the flagged set is concentrated in
# 2023-24, so an unmatched sample would credit that skew to the detector.
import csv, random
from collections import defaultdict

touched = {r["repo_name"] for r in
           csv.DictReader(open(D + "starscout/250101/fake_stars_low_activity_repos.csv"))}
touched |= {r["repo_name"] for r in
            csv.DictReader(open(D + "starscout/250101/fake_stars_clustered_repos.csv"))}
touched |= set(flagged)

spiky_by_month = defaultdict(list)
for r in csv.DictReader(open(D + "starscout/all_github_repos_with_spikes.csv")):
    if r["repo"] not in touched:
        spiky_by_month[r["month"]].append(r["repo"])

# Each flagged repo's campaign month, so the control can mirror the distribution.
campaign_month = {}
for row in ref["by_month"]:
    if row["anomaly"] and row["repo"] not in campaign_month:
        campaign_month[row["repo"]] = row["month"]

rng = random.Random(42)
for month in spiky_by_month:
    rng.shuffle(spiky_by_month[month])
cursor = defaultdict(int)
control, unmatched = [], 0
for repo in flagged:
    month = campaign_month.get(repo)
    pool = spiky_by_month.get(month, [])
    if cursor[month] < len(pool):
        control.append(pool[cursor[month]])
        cursor[month] += 1
    else:
        unmatched += 1
print(f"control: {len(control)} month-matched, {unmatched} flagged repos had no "
      f"unflagged peer left in their month", file=sys.stderr)

res_flagged = run("flagged", flagged)
res_control = run("control", control)


def summarise(recs: list[dict]) -> dict:
    alive = [r for r in recs if r["alive"] is True]
    gone = [r for r in recs if r["alive"] is False]
    errors = [r for r in recs if r["alive"] is None]
    renamed = [r for r in alive if r["now"].lower() != r["repo"].lower()]
    decided = len(alive) + len(gone)
    return {
        "n": len(recs),
        "alive": len(alive),
        "gone": len(gone),
        "errors": len(errors),
        "gone_pct": len(gone) / decided if decided else None,
        "renamed": len(renamed),
        "archived": sum(1 for r in alive if r["archived"]),
    }


out = {
    "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "flagged": summarise(res_flagged),
    "control": summarise(res_control),
    "records": {r["repo"]: r for r in res_flagged},
}
json.dump(out, open(D + "survival.json", "w"))

for k in ("flagged", "control"):
    s = out[k]
    print(f"{k:8} gone {s['gone']}/{s['alive'] + s['gone']} = {s['gone_pct']:.2%}"
          f"   alive {s['alive']}  renamed {s['renamed']}  archived {s['archived']}"
          f"  errors {s['errors']}", file=sys.stderr)
