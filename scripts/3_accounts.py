"""Ask the same survival question one level down: not the repos, the accounts.

Step 2 shows GitHub removed 92.8% of the flagged repositories. That says the
detector pointed at something real, but not what GitHub was reacting to -- a
repo can be taken down for its payload, and its stars go with it. The account
side separates the two, and it also answers the question people actually ask
about star buying: does GitHub punish accounts for starring a lot?

Method. Take one day inside the detection window and before the archive
collapsed (2024-07, the paper's peak month), read three hours of GH Archive
spread across the clock, and split every WatchEvent actor in two:

    treatment  starred at least one flagged repo in that hour
    control    starred only repos the detector never touched

Then look every one of them up today. GraphQL `user(login:)` returns null for
an account that is deleted, suspended or renamed -- the three are not
distinguishable from outside, so "gone" means all three. Organizations cannot
star, so a null is never just an org.

This is a deliberately weak treatment: it catches anyone who happened to star a
flagged repo that hour, real users included. The paper's postprocessed account
set is far purer (57.07% deleted as of 2025-01, against a 3.54% baseline). A
diluted treatment can only understate the gap, which is the safe direction.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import gzip, io, json, random, ssl, subprocess, sys, time, urllib.error, urllib.request
from collections import Counter

API = "https://api.github.com/graphql"
CTX = ssl.create_default_context()
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                       check=True).stdout.strip()
if not TOKEN:
    sys.exit("no GitHub token: run `gh auth login` first")

DAY = "2024-07-16"      # inside the detection window, before the archive decayed
HOURS = [3, 11, 19]     # spread across the clock so one timezone does not dominate
CONTROL_N = 2000        # control is far larger than treatment; sample it down
BATCH = 40
FIELDS = "login createdAt starredRepositories{totalCount} repositories{totalCount}"


def wait_for_reset(header=None):
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
    print(f"  rate limited; sleeping {delay}s", file=sys.stderr)
    time.sleep(delay)


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


# ------------------------------------------------------------------- archive
def watch_actors(flagged: set) -> tuple:
    """Actors of every WatchEvent in the sampled hours, split by what they starred."""
    treat, control = {}, {}
    for hour in HOURS:
        # GH Archive does not zero-pad the hour: -3, not -03.
        url = f"https://data.gharchive.org/{DAY}-{hour}.json.gz"
        print(f"  {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers={"User-Agent": "github-stars/1.0"})
        with urllib.request.urlopen(req, context=CTX, timeout=300) as r:
            raw = r.read()
        n = 0
        with gzip.open(io.BytesIO(raw), "rt", errors="replace") as f:
            for line in f:
                # Cheap string test first; parsing all 1.7M lines is the slow path.
                if '"type":"WatchEvent"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n += 1
                repo = e["repo"]["name"].lower()
                (treat if repo in flagged else control)[e["actor"]["login"]] = repo
        print(f"    {n:,} WatchEvents", file=sys.stderr)
    # One flagged star is enough to move an actor out of the control group.
    for login in treat:
        control.pop(login, None)
    return treat, control


# ------------------------------------------------------------------- lookups
def fetch(chunk: list, seen: dict):
    """Look up a batch, halving it if the server refuses the whole thing."""
    q = "{" + "\n".join('u%d: user(login:%s){%s}' % (i, json.dumps(l), FIELDS)
                        for i, l in enumerate(chunk)) + "}"
    try:
        res = call(q)
        data = res.get("data")
        # No `data` at all means the request failed. Recording that as "every
        # account in this batch is gone" would corrupt the one number this
        # script produces, so split instead and let a single login carry it.
        if not isinstance(data, dict):
            raise RuntimeError(json.dumps(res)[:200])
    except Exception as e:
        if len(chunk) == 1:
            print(f"  giving up on {chunk[0]}: {e}", file=sys.stderr)
            seen[chunk[0]] = {"alive": None}
            return
        mid = len(chunk) // 2
        fetch(chunk[:mid], seen)
        fetch(chunk[mid:], seen)
        return
    for i, login in enumerate(chunk):
        node = data.get(f"u{i}")
        if node is None:
            seen[login] = {"alive": False}
        else:
            seen[login] = {"alive": True,
                           "created_at": node["createdAt"],
                           "starred": node["starredRepositories"]["totalCount"],
                           "repos": node["repositories"]["totalCount"]}


def run(name: str, logins: list) -> dict:
    ckpt = Path(D + f"accounts_{name}.json")
    seen = json.loads(ckpt.read_text()) if ckpt.exists() else {}
    seen = {k: v for k, v in seen.items() if v.get("alive") is not None}
    todo = [l for l in logins if l not in seen]
    for i in range(0, len(todo), BATCH):
        fetch(todo[i:i + BATCH], seen)
        ckpt.write_text(json.dumps(seen))
        print(f"\r  {name} {min(i + BATCH, len(todo)):,}/{len(todo):,}", end="", file=sys.stderr)
    print(file=sys.stderr)

    got = [seen[l] for l in logins if l in seen and seen[l].get("alive") is not None]
    gone = sum(1 for r in got if not r["alive"])
    starred = sorted(r["starred"] for r in got if r["alive"])
    # Buckets, not just a median: the whole point is the shape of the two
    # distributions, and a median hides that one side is a wall at 0 and 1.
    def share(lo, hi):
        return sum(1 for x in starred if lo <= x < hi) / len(starred)
    return {
        "n": len(logins), "resolved": len(got), "gone": gone,
        "gone_pct": gone / len(got),
        "alive": len(starred),
        "starred_median": starred[len(starred) // 2],
        "starred_p90": starred[int(0.9 * len(starred))],
        "starred_max": max(starred),
        "starred_buckets": [
            ["0", share(0, 1)], ["1", share(1, 2)], ["2-9", share(2, 10)],
            ["10-99", share(10, 100)], ["100-999", share(100, 1000)],
            ["1k-9999", share(1000, 10000)], ["10k+", share(10000, 10 ** 9)],
        ],
        "over_5k": sum(1 for x in starred if x > 5000),
    }


ref = json.load(open(D + "reference.json"))
flagged = {r["repo"].lower() for r in ref["repos"]}
print(f"flagged repos: {len(flagged):,}", file=sys.stderr)

treat, control = watch_actors(flagged)
random.seed(7)
control_sample = sorted(random.sample(sorted(control), min(CONTROL_N, len(control))))
print(f"treatment {len(treat):,}  control {len(control):,} "
      f"(sampled {len(control_sample):,})", file=sys.stderr)

out = {
    "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "day": DAY, "hours": HOURS,
    "treatment": run("treatment", sorted(treat)),
    "control": run("control", control_sample),
    # The paper's own account numbers, for the reader to compare against.
    "paper": {"as_of": "2025-01", "campaign_gone": 0.5707, "baseline_gone": 0.0354},
}
json.dump(out, open(D + "accounts.json", "w"), ensure_ascii=False)

for k in ("treatment", "control"):
    r = out[k]
    print(f"{k:10} n={r['n']:>5}  gone={r['gone']:>5} ({r['gone_pct']:.2%})  "
          f"survivors starred: median={r['starred_median']:,} "
          f"p90={r['starred_p90']:,} max={r['starred_max']:,}", file=sys.stderr)
