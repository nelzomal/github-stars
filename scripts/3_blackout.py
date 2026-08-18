"""Measure what is left of the public data these detectors were built on.

Two channels ever let an outsider audit a repository's stars:

  1. the stargazer list  -- who starred this repo, and when
  2. GH Archive          -- the replayable stream of every public GitHub event,
                            which is where the WatchEvents live

This script probes both, today, and samples GH Archive's event mix back to 2019
so the second one can be dated rather than asserted.

Sampling note: GH Archive hourly files run 10-100 MB gzipped and there are
~62,000 of them in the window. This reads the first PREFIX_MB of each sampled
hour instead of the whole file -- enough events for a type ratio, and gzip
decodes a truncated stream fine. scripts/analysis/prefix_bias.py checks the
prefix ratio against the full file for the hours where both were fetched.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import gzip, json, ssl, subprocess, sys, time, urllib.error, urllib.request, zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

CTX = ssl.create_default_context()
UA = "github-stars/1.0"
PREFIX_MB = 4
HOURS = [1, 9, 17]  # three hours per sampled day, spread across time zones
ARCHIVE = "https://data.gharchive.org/%s-%d.json.gz"  # hour is NOT zero-padded


def sampled_days() -> list[str]:
    """The 16th of every month from GH Archive's start to last month."""
    out, y, m = [], 2019, 7
    now = time.gmtime()
    while (y, m) < (now.tm_year, now.tm_mon):
        out.append(f"{y:04d}-{m:02d}-16")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def event_mix(day: str, hour: int) -> Counter:
    """Event-type counts from the first PREFIX_MB of one hourly archive file."""
    url = ARCHIVE % (day, hour)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Range": f"bytes=0-{PREFIX_MB * 1024 * 1024 - 1}"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=180) as r:
            blob = r.read()
    except urllib.error.HTTPError as e:
        return Counter({"_http_%d" % e.code: 1})
    except Exception:
        return Counter({"_error": 1})

    counts = Counter()
    dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        text = dec.decompress(blob).decode("utf-8", "replace")
    except zlib.error:
        return Counter({"_corrupt": 1})
    for line in text.split("\n")[:-1]:  # drop the partial last line
        i = line.find('"type":"')
        if i >= 0:
            counts[line[i + 8:line.find('"', i + 8)]] += 1
    counts["_total"] = sum(v for k, v in counts.items() if not k.startswith("_"))
    return counts


def probe_day(day: str) -> dict:
    total = Counter()
    for h in HOURS:
        total += event_mix(day, h)
    n = total.get("_total", 0)
    return {
        "day": day,
        "events": n,
        "hours": len(HOURS),
        "by_type": {k: v for k, v in total.items() if not k.startswith("_")},
        "p_watch": total.get("WatchEvent", 0) / n if n else None,
        "p_fork": total.get("ForkEvent", 0) / n if n else None,
        "p_push": total.get("PushEvent", 0) / n if n else None,
        "p_issue_comment": total.get("IssueCommentEvent", 0) / n if n else None,
    }


# --------------------------------------------------------------- live probes
def http(url: str, headers: dict = None, method: str = "GET") -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})},
                                 method=method)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            return {"status": r.status, "body": r.read(2000).decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read(2000).decode("utf-8", "replace")}
    except Exception as e:
        return {"status": None, "body": str(e)[:300]}


def live_probes() -> dict:
    token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                           text=True).stdout.strip()
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    # A repo nobody involved here administers, so it exercises the public path.
    target = "torvalds/linux"

    out = {"target": target}
    r = http(f"https://api.github.com/repos/{target}/stargazers?per_page=2")
    out["rest_anon"] = {"status": r["status"],
                        "message": json.loads(r["body"]).get("message")
                        if r["body"].startswith("{") else None}
    r = http(f"https://api.github.com/repos/{target}/stargazers?per_page=2", auth)
    out["rest_auth"] = {"status": r["status"],
                        "message": json.loads(r["body"]).get("message")
                        if r["body"].startswith("{") else None}
    r = http(f"https://github.com/{target}/stargazers")
    out["html"] = {"status": r["status"]}

    # The exact query the paper's collector used to enumerate stargazers.
    q = ('{repository(owner:"torvalds",name:"linux"){stargazerCount '
         'stargazers(first:5,orderBy:{field:STARRED_AT,direction:DESC})'
         '{totalCount edges{starredAt node{login}}}}}')
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": q}).encode(),
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          **auth})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = {"http_error": e.code}
    repo = ((body.get("data") or {}).get("repository") or {})
    out["graphql"] = {
        "stargazerCount": repo.get("stargazerCount"),
        "edges_returned": len((repo.get("stargazers") or {}).get("edges") or []),
        "errors": [e.get("message", "")[:200] for e in (body.get("errors") or [])],
    }

    # Does GitHub's own public timeline still carry star events? This decides
    # whether the archive gap is GitHub withholding them or the archive missing
    # them, so it is the difference between two very different sentences.
    tl = Counter()
    for page in range(1, 6):
        req = urllib.request.Request(
            f"https://api.github.com/events?per_page=100&page={page}",
            headers={"User-Agent": UA, **auth})
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
                events = json.loads(r.read())
        except urllib.error.HTTPError as e:
            tl[f"_http_{e.code}"] += 1
            break
        for ev in events:
            tl[ev["type"]] += 1
    n = sum(v for k, v in tl.items() if not k.startswith("_"))
    out["public_timeline"] = {
        "events": n,
        "by_type": dict(tl),
        "p_watch": tl.get("WatchEvent", 0) / n if n else None,
    }
    return out


days = sampled_days()
print(f"sampling {len(days)} months x {len(HOURS)} hours of GH Archive "
      f"({PREFIX_MB} MB prefix each)...", file=sys.stderr)
with ThreadPoolExecutor(12) as ex:
    archive = list(ex.map(probe_day, days))

print("probing live endpoints...", file=sys.stderr)
out = {
    "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "prefix_mb": PREFIX_MB,
    "hours_per_day": HOURS,
    "archive": archive,
    "live": live_probes(),
}
json.dump(out, open(D + "blackout.json", "w"))

for a in archive:
    if a["p_watch"] is None:
        print(f"  {a['day']}  no data", file=sys.stderr)
    elif a["day"][:4] in ("2019", "2022", "2025", "2026") and a["day"][5:7] in ("01", "07", "08"):
        print(f"  {a['day']}  {a['events']:7d} events  watch {a['p_watch']:6.2%}"
              f"  fork {a['p_fork']:5.2%}  push {a['p_push']:6.2%}", file=sys.stderr)
L = out["live"]
print(f"stargazers REST anon  {L['rest_anon']['status']}  {L['rest_anon']['message']}", file=sys.stderr)
print(f"stargazers REST auth  {L['rest_auth']['status']}  {L['rest_auth']['message']}", file=sys.stderr)
print(f"stargazers HTML       {L['html']['status']}", file=sys.stderr)
print(f"GraphQL stargazers    count={L['graphql']['stargazerCount']} "
      f"edges={L['graphql']['edges_returned']} errors={L['graphql']['errors']}", file=sys.stderr)
print(f"public timeline       {L['public_timeline']['events']} events, "
      f"watch {L['public_timeline']['p_watch']}", file=sys.stderr)
