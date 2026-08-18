"""Run what is left of the fake-star heuristics against named repositories.

    python3 scripts/probe_repo.py owner/repo [owner/repo ...]

StarScout's low-activity signature is "the account's whole history is one star".
The paper evaluated that over GH Archive because it ran at six-billion-event
scale; for a handful of repos it can be asked directly, because two endpoints
survived the 2026 shutdown:

    GET /repos/{o}/{r}/events   recent WatchEvents, with actor and timestamp
    GraphQL user.starredRepositories.totalCount   how many repos an account starred

What that buys, and what it does not:

  * The events endpoint is capped at 300 events over 3 pages. On a repo getting
    ~100 stars a day that is a ~2-day window, and it is the *most recent* stars,
    not a sample of the repo's history. A campaign that ran last year is
    invisible here. This measures the repo's stargazers **now**.
  * The lockstep signature cannot be run at all. It needs the full account x
    repo bipartite graph to find groups starring the same set of repos in the
    same window; nothing public exposes that any more.

So this is a smoke test, not the detector. Pass several repos and read the
columns against each other -- an isolated number means very little.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import json, ssl, statistics, subprocess, sys, time, urllib.error, urllib.request
from collections import Counter

CTX = ssl.create_default_context()
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                       check=True).stdout.strip()
HDR = {"Authorization": f"Bearer {TOKEN}", "User-Agent": "github-stars/1.0"}
NEW_ACCOUNT_DAYS = 30


def rest(path: str):
    req = urllib.request.Request("https://api.github.com/" + path, headers=HDR)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code}


def graphql(query: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={**HDR, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
        return json.loads(r.read())


def stargazers(repo: str) -> list:
    """Recent WatchEvents for one repo. Three pages is the server's limit."""
    out, seen = [], set()
    for page in range(1, 4):
        events = rest(f"repos/{repo}/events?per_page=100&page={page}")
        if isinstance(events, dict):  # error payload
            break
        for e in events:
            if e["type"] != "WatchEvent":
                continue
            login = e["actor"]["login"]
            if login in seen:
                continue
            seen.add(login)
            out.append({"login": login, "at": e["created_at"]})
    return out


FIELDS = ("login createdAt followers{totalCount} following{totalCount} "
          "repositories{totalCount} gists{totalCount} "
          "starredRepositories{totalCount} "
          "contributionsCollection{contributionCalendar{totalContributions}}")


def profile(logins: list) -> dict:
    out = {}
    for i in range(0, len(logins), 25):
        chunk = logins[i:i + 25]
        q = "{" + "\n".join(
            f'u{j}: user(login:{json.dumps(l)}){{{FIELDS}}}'
            for j, l in enumerate(chunk)) + "}"
        res = graphql(q)
        data = res.get("data") or {}
        for j, l in enumerate(chunk):
            n = data.get(f"u{j}")
            if not n:
                continue  # deleted account, or an org rather than a user
            out[l] = {
                "created_at": n["createdAt"],
                "followers": n["followers"]["totalCount"],
                "following": n["following"]["totalCount"],
                "repos": n["repositories"]["totalCount"],
                "gists": n["gists"]["totalCount"],
                "starred": n["starredRepositories"]["totalCount"],
                "contributions":
                    n["contributionsCollection"]["contributionCalendar"]["totalContributions"],
            }
    return out


def age_days(iso: str) -> float:
    return (time.time() - time.mktime(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))) / 86400


def analyse(repo: str) -> dict:
    stars = stargazers(repo)
    if not stars:
        return {"repo": repo, "n": 0}
    prof = profile([s["login"] for s in stars])
    got = [s for s in stars if s["login"] in prof]
    p = [prof[s["login"]] for s in got]

    times = sorted(time.mktime(time.strptime(s["at"], "%Y-%m-%dT%H:%M:%SZ")) for s in got)
    span_h = (times[-1] - times[0]) / 3600 if len(times) > 1 else 0
    # Tightest 60-second cluster: merchants deliver in batches, humans do not.
    burst = max((sum(1 for t2 in times if t <= t2 < t + 60) for t in times), default=0)

    def share(fn):
        return sum(1 for x in p if fn(x)) / len(p)

    return {
        "repo": repo,
        "n": len(got),
        "unresolved": len(stars) - len(got),
        "span_h": span_h,
        "burst60": burst,
        # StarScout's low-activity signature, asked directly.
        "only_star": share(lambda x: x["starred"] == 1),
        "no_repos": share(lambda x: x["repos"] == 0),
        "no_followers": share(lambda x: x["followers"] == 0),
        "new_account": share(lambda x: age_days(x["created_at"]) < NEW_ACCOUNT_DAYS),
        "no_contrib": share(lambda x: x["contributions"] == 0),
        # All four at once: no repos, no followers, no contributions, one star.
        "empty": share(lambda x: x["repos"] == 0 and x["followers"] == 0
                       and x["contributions"] == 0 and x["starred"] <= 1),
        "median_age_d": statistics.median(age_days(x["created_at"]) for x in p),
        "median_starred": statistics.median(x["starred"] for x in p),
        "median_contrib": statistics.median(x["contributions"] for x in p),
    }


repos = sys.argv[1:]
if not repos:
    sys.exit(__doc__)

rows = [analyse(r) for r in repos]

print(f"\n最近的星标账号画像（{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}）")
print("样本 = 该仓库最近的 WatchEvent，上限 300 条事件\n")
hdr = (f"{'仓库':<32}{'样本':>5}{'跨度h':>7}{'60秒内最多':>10}"
       f"{'只星过1个':>10}{'0仓库':>8}{'0粉丝':>8}{'新号<30d':>9}"
       f"{'四项全空':>9}{'账号年龄中位(天)':>16}{'星标数中位':>11}")
print(hdr)
print("-" * 150)
for r in rows:
    if not r["n"]:
        print(f"{r['repo']:<32}  取不到事件")
        continue
    print(f"{r['repo']:<32}{r['n']:>5}{r['span_h']:>7.1f}{r['burst60']:>10}"
          f"{r['only_star']:>10.1%}{r['no_repos']:>8.1%}{r['no_followers']:>8.1%}"
          f"{r['new_account']:>9.1%}{r['empty']:>9.1%}"
          f"{r['median_age_d']:>16,.0f}{r['median_starred']:>11,.0f}")

json.dump({"measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rows": rows}, open(D + "probe_repo.json", "w"), ensure_ascii=False)
print(f"\n注意：只覆盖最近 {max(r.get('span_h', 0) for r in rows):.0f} 小时左右的星标，"
      f"查不到历史；同步刷星（lockstep）签名在今天的公开数据下完全跑不了。")
