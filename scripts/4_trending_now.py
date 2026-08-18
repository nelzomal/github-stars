"""What can still be checked about a trending repository now that the
stargazer list is gone.

Scrapes github.com/trending across languages and windows, then asks the API for
every ratio that survives the shutdown: forks against stars, contributors
against stars, commits, issues, releases, age. None of these prove anything on
their own -- they are what is left to look at.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import json, re, ssl, subprocess, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

CTX = ssl.create_default_context()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                       check=True).stdout.strip()

LANGS = ["", "python", "javascript", "typescript", "go", "rust", "java", "c++",
         "c", "c#", "php", "ruby", "shell", "html", "jupyter-notebook", "swift",
         "kotlin", "dart", "lua", "zig"]
SPANS = ["daily", "weekly", "monthly"]

ROW = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
NAME = re.compile(r'<h2[^>]*>\s*<a href="/([^"]+?)"', re.S)
NAME_ALT = re.compile(r'href="/([\w.-]+/[\w.-]+)/stargazers"')
STARS_PERIOD = re.compile(r'([\d,]+)\s*stars?\s+(?:today|this week|this month)')


def trending(lang: str, span: str) -> dict:
    url = f"https://github.com/trending/{lang}?since={span}" if lang \
        else f"https://github.com/trending?since={span}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        return {"lang": lang, "span": span, "error": str(e)[:200], "repos": []}
    repos = []
    for block in ROW.findall(html):
        m = NAME.search(block) or NAME_ALT.search(block)
        if not m:
            continue
        name = m.group(1)
        # Logged-out pages wrap the title in a sign-in redirect.
        if name.startswith("login?"):
            name = urllib.parse.unquote(name.split("return_to=%2F")[-1])
        if name.count("/") != 1:
            continue
        p = STARS_PERIOD.search(block)
        repos.append({"repo": name,
                      "stars_this_period": int(p.group(1).replace(",", "")) if p else None})
    return {"lang": lang, "span": span, "n_rows": len(repos), "repos": repos}


FIELDS = """nameWithOwner description isArchived isFork createdAt pushedAt
    stargazerCount forkCount watchers{totalCount} issues{totalCount}
    pullRequests{totalCount} releases{totalCount} mentionableUsers{totalCount}
    primaryLanguage{name}
    defaultBranchRef{target{... on Commit{history(first:0){totalCount}}}}"""


def graphql(repos: list, tries: int = 3) -> dict:
    """Batch lookup, halving on failure.

    Trending lists contain repos with hundreds of thousands of commits, and a
    batch holding one of those times out server-side (502/504). Splitting
    isolates the expensive repo instead of losing everything alongside it.
    """
    for attempt in range(tries):
        try:
            return graphql_once(repos)
        except Exception as e:
            if "rate limited" in str(e) or "403" in str(e) or "429" in str(e):
                continue
            if len(repos) > 1:
                mid = len(repos) // 2
                return {**graphql(repos[:mid]), **graphql(repos[mid:])}
            if attempt == tries - 1:
                print(f"  giving up on {repos[0]}: {str(e)[:120]}", file=sys.stderr)
                return {}
            time.sleep(2 ** attempt)
    return {}


_reset_lock = threading.Lock()


def wait_for_reset():
    """Sleep until the GraphQL budget refills rather than spending retries on a
    limit that lifts at a known wall-clock time."""
    with _reset_lock:
        try:
            out = subprocess.run(["gh", "api", "rate_limit", "--jq",
                                  ".resources.graphql | [.remaining, .reset] | @tsv"],
                                 capture_output=True, text=True, timeout=60).stdout.split()
            remaining, reset = int(out[0]), int(out[1])
        except Exception:
            remaining, reset = 0, int(time.time()) + 60
        if remaining > 100:
            return
        delay = max(reset - int(time.time()), 0) + 5
        print(f"  rate limited; sleeping {delay}s", file=sys.stderr)
        time.sleep(delay)


def graphql_once(repos: list) -> dict:
    parts = ['r%d: repository(owner:%s, name:%s){%s}'
             % (i, json.dumps(r.split("/")[0]), json.dumps(r.split("/", 1)[1]), FIELDS)
             for i, r in enumerate(repos)]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": "{" + "\n".join(parts) + "}"}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "github-stars/1.0"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=180) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            wait_for_reset()
            raise
        raise
    if any(e.get("type") == "RATE_LIMITED" for e in (res.get("errors") or [])):
        wait_for_reset()
        raise RuntimeError("rate limited")
    data = res.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(json.dumps(res)[:300])
    out = {}
    for i, name in enumerate(repos):
        node = data.get(f"r{i}")
        if not node:
            continue
        commits = (((node.get("defaultBranchRef") or {}).get("target") or {})
                   .get("history") or {}).get("totalCount")
        out[name] = {
            "repo": node["nameWithOwner"],
            "description": (node.get("description") or "")[:300],
            "language": (node.get("primaryLanguage") or {}).get("name"),
            "archived": node["isArchived"], "fork": node["isFork"],
            "created_at": node["createdAt"], "pushed_at": node["pushedAt"],
            "stars": node["stargazerCount"], "forks": node["forkCount"],
            "watchers": node["watchers"]["totalCount"],
            "issues": node["issues"]["totalCount"],
            "prs": node["pullRequests"]["totalCount"],
            "releases": node["releases"]["totalCount"],
            "contributors": node["mentionableUsers"]["totalCount"],
            "commits": commits,
        }
    return out


print(f"scraping github.com/trending: {len(LANGS)} languages x {len(SPANS)} windows",
      file=sys.stderr)
jobs = [(l, s) for l in LANGS for s in SPANS]
with ThreadPoolExecutor(6) as ex:
    pages = list(ex.map(lambda j: trending(*j), jobs))

seen = {}
for p in pages:
    for r in p["repos"]:
        e = seen.setdefault(r["repo"], {"repo": r["repo"], "listings": []})
        e["listings"].append({"lang": p["lang"], "span": p["span"],
                              "stars_this_period": r["stars_this_period"]})

names = sorted(seen)
print(f"{len(names)} distinct repos across {sum(p.get('n_rows', 0) for p in pages)} listings",
      file=sys.stderr)

info = {}
for i in range(0, len(names), 50):
    info.update(graphql(names[i:i + 50]))

now = time.time()
rows = []
for name in names:
    d = info.get(name)
    if not d:
        continue
    age_days = max((now - time.mktime(time.strptime(d["created_at"], "%Y-%m-%dT%H:%M:%SZ"))) / 86400, 1)
    stars = d["stars"] or 0
    rows.append({**d,
                 "listings": seen[name]["listings"],
                 "age_days": round(age_days, 1),
                 "fork_star": round(d["forks"] / stars, 4) if stars else None,
                 "stars_per_contributor": round(stars / d["contributors"], 1) if d["contributors"] else None,
                 "stars_per_commit": round(stars / d["commits"], 2) if d.get("commits") else None,
                 "stars_per_day": round(stars / age_days, 1)})

out = {
    "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "pages": [{"lang": p["lang"], "span": p["span"], "n_rows": p.get("n_rows", 0),
               "error": p.get("error")} for p in pages],
    "repos": rows,
}
json.dump(out, open(D + "trending_now.json", "w"))

rows_per_page = [p["n_rows"] for p in pages if p.get("n_rows")]
print(f"listing sizes: min {min(rows_per_page)} max {max(rows_per_page)} "
      f"(the page used to hold 25)", file=sys.stderr)
lo = sorted([r for r in rows if r["fork_star"] is not None], key=lambda r: r["fork_star"])[:8]
print("lowest fork:star ratios among today's trending repos:", file=sys.stderr)
for r in lo:
    print(f"  {r['fork_star']:.4f}  {r['repo'][:44]:44} {r['stars']:7d} stars "
          f"{r['contributors']:5d} contributors", file=sys.stderr)
