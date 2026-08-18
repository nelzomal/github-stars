"""Fold the five data files into the single blob the page inlines.

Naming rule, applied here rather than in the template so it is checkable:
a repository is named on the page only if GitHub has already removed it. The
detector's precision cannot be measured -- there is no way to verify whether a
single star was bought -- so the paper reasons from a hypothetical 99%, which
still leaves ~180 wrong entries out of 18.6k. A live project should not be
labelled a star buyer by a page its maintainer cannot answer back on. Deleted
repos carry no such risk, and they are where the malware is.
"""

from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
import json, re, sys
from collections import defaultdict, Counter

ref = json.load(open(D + "reference.json"))
survival = json.load(open(D + "survival.json"))
blackout = json.load(open(D + "blackout.json"))
trending_hist = json.load(open(D + "trending_hist.json"))
trending_now = json.load(open(D + "trending_now.json"))

# ------------------------------------------------------------- categorisation
# The 580 hand-coded repos use the authors' label. The rest are almost all
# deleted, leaving only a name -- the same position the paper was in, and it
# resorted to the same token frequencies (free 856, crack 721, bot 1071,
# roblox 252). Longest-standing patterns first; `other` is not a guess.
TOKENS = [
    ("薅羊毛 / 自动点击", """autoclicker clicker autoclick autofarm farm farmer tapper
        tap taps blum hamster kombat catizen yescoin memefi pocketfi tapswap notcoin
        hrum tomarket bcoin2048 cubes banana seed autobot clickbot tapbot airdropbot"""),
    ("盗版软件 / 破解", """free fr33 crack cracked cracker keygen activation activator
        activated nulled warez serial license licence patcher patch premium full
        version latest repack adobe photoshop illustrator premiere aftereffects
        lightroom acrobat autocad sketchup sonyvegas vegas filmora voicemod davinci
        resolve exitlag tenorshare windscribe sapphire boris spotify netflix office365
        office idm winrar ccleaner malwarebytes downloader download software setup
        installer"""),
    ("游戏外挂 / 脚本执行器", """hack hacks hck h4ck cheat cheats cheto aimbot esp spoofer
        injector unlocker exploit exploits modmenu mods devmode fivem valorant fortnite
        roblox blooket krnl bloxstrap csgo cs2 apex warframe valheim minecraft eldenring
        gta5 gta pubg executor solara wave octo hydrogen fluxus arceus synapse evon
        codex trigon delta menu script scripts externalcheat internalcheat"""),
    ("机器人 / 账号工具", """bot bots selfbot discord telegram nitro generator gen checker
        account accounts spammer raider token tokens invite views viewer view followers
        likes subs boosting boost"""),
    ("加密货币", """crypto wallet wallets bitcoin btc eth ethereum solana binance tron
        ton airdrop miner mining defi metamask trading tradingview tradingbot pumpfun
        sniper drainer stealer seedphrase phrase mnemonic bruteforce"""),
    ("AI / 大模型", """ai llm gpt chatgpt agent agents rag prompt prompts diffusion
        langchain openai claude gemini deepseek mcp"""),
    ("区块链", "blockchain web3 nft dao smartcontract solidity zk rollup"),
]
TOKENS = [(zh, set(s.split())) for zh, s in TOKENS]

# Names like "Overwatchhack-liah" or "PhotoshopFullVersion" run the giveaway
# together with other words, so a token split misses them. These stems are long
# and distinctive enough to match inside a word without dragging in ordinary
# English -- which is why "free", "bot", "gen" and "ai" are not among them.
STEMS = [
    ("游戏外挂 / 脚本执行器", """hack cheat aimbot spoofer injector roblox fortnite valorant
        minecraft overwatch csgo warzone"""),
    ("盗版软件 / 破解", "crack keygen activator nulled warez torrent downloader photoshop"),
    ("薅羊毛 / 自动点击", "autoclick clicker autofarm tapswap hamster"),
    ("加密货币", "wallet airdrop drainer stealer metamask"),
]
STEMS = [(zh, s.split()) for zh, s in STEMS]

LABEL_ZH = {
    "suspicious": "垃圾 / 钓鱼", "ai": "AI / 大模型", "blockchain": "区块链",
    "tool/application": "工具 / 应用", "tutorial/demo": "教程 / 演示",
    "web": "Web 框架", "basic-utility": "基础工具", "database": "数据库",
    "bot": "机器人 / 账号工具", "other": "其它",
}


def categorise(repo: str, domain) -> str:
    # A hand-coded label beats any guess; "deleted" is a status, not a domain.
    if domain and domain != "deleted" and domain in LABEL_ZH:
        return LABEL_ZH[domain]
    low = repo.lower()
    toks = set(re.split(r"[^a-z0-9]+", low))
    for zh, vocab in TOKENS:
        if toks & vocab:
            return zh
    for zh, stems in STEMS:
        if any(s in low for s in stems):
            return zh
    return "未分类"


# ------------------------------------------------------------------ per repo
alive_of = {}
for repo, rec in survival["records"].items():
    alive_of[repo] = rec.get("alive")

by_month = defaultdict(list)
for row in ref["by_month"]:
    by_month[row["repo"]].append(row)

trending_first = {m["repo"]: m["first_trending"] for m in trending_hist["matched"]}

repos = []
id_of = {}  # real name -> page id, so withheld repos stay linkable by number
for r in ref["repos"]:
    name = r["repo"]
    id_of[name] = len(repos)
    alive = alive_of.get(name)
    months = sorted(by_month.get(name, []), key=lambda x: x["month"])
    rec = survival["records"].get(name) or {}
    repos.append({
        # Live repos keep their category and numbers but lose their name.
        "name": name if alive is False else None,
        "id": len(repos),
        "alive": alive,
        "cat": categorise(name, r["domain"]),
        "labelled": bool(r["domain"]),
        "n_stars": r["n_stars"],
        "n_fake": r["n_fake"],
        "p_fake": r["p_fake"],
        "trending": trending_first.get(name),
        "packages": r["packages"],
        "months": [[m["month"], m["n_stars"], m["n_fake"]] for m in months],
        "stars_now": rec.get("stars"),
        "forks_now": rec.get("forks"),
        "contributors_now": rec.get("contributors"),
    })

# ------------------------------------------------------------- flame hierarchy
# status -> category -> repo -> month, width = stars.
def node(name, value, children=None, extra=None):
    n = {"n": name, "v": value}
    if children:
        n["c"] = children
    if extra:
        n.update(extra)
    return n


CAP = 400  # repos drawn individually per category; the rest become one bar
STATUS = [("已被 GitHub 删除", False), ("仍然在线", True), ("查询失败", None)]
flame = []
for status_name, want in STATUS:
    group = [r for r in repos if r["alive"] is want]
    if not group:
        continue
    cats = []
    for cat, members in sorted(Counter(r["cat"] for r in group).items(),
                               key=lambda kv: -kv[1]):
        rs = [r for r in group if r["cat"] == cat]
        rs.sort(key=lambda r: -r["n_stars"])
        shown, rest = rs[:CAP], rs[CAP:]
        children = [
            # The month layer is what makes this file big, so it is carried only
            # for the repos wide enough to click; below that a repo is a leaf.
            node(r["name"] or f"（仍在线 #{r['id']}）", r["n_stars"],
                 [node(m[0], m[1], None, {"f": m[2]}) for m in r["months"]] if i < 60 else None,
                 {"f": r["n_fake"], "p": r["p_fake"], "t": r["trending"],
                  "id": r["id"], "alive": r["alive"]})
            for i, r in enumerate(shown)
        ]
        # The tail is unreadable one bar at a time but it is not nothing, so it
        # stays as a single bar. Without it the children would not add up to the
        # parent and every ratio above this row would be quietly wrong.
        if rest:
            children.append(node(f"其余 {len(rest):,} 个仓库",
                                 sum(r["n_stars"] for r in rest), None,
                                 {"f": sum(r["n_fake"] for r in rest), "rest": len(rest)}))
        cats.append(node(cat, sum(r["n_stars"] for r in rs), children,
                         {"f": sum(r["n_fake"] for r in rs), "repos": len(rs)}))
    flame.append(node(status_name, sum(r["n_stars"] for r in group), cats,
                      {"f": sum(r["n_fake"] for r in group), "repos": len(group)}))

# ------------------------------------------------------- timeline exhibit set
# Repos that reached Trending, ordered by how much of the whole star history
# landed in its single worst month. That ranking puts the one-month spikes at
# the top, which is the shape the section exists to show; a repo whose faking
# was spread thin reads as noise and sinks.
def burst(r):
    if not r["months"] or not r["n_stars"]:
        return 0
    return max(m[2] for m in r["months"]) / r["n_stars"]


timeline = sorted([r for r in repos if r["trending"]],
                  key=lambda r: (-burst(r), -r["n_stars"]))

out = {
    "meta": {
        "built_at": survival["checked_at"],
        "window": ref["source"]["window"],
        "source": ref["source"],
        "archive": trending_hist["archive"],
        "trending_measured_at": trending_now["measured_at"],
        "blackout_measured_at": blackout["measured_at"],
    },
    "totals": {
        **ref["totals"],
        "ever_trending": trending_hist["totals"]["ever_trending"],
        "ever_trending_in_window": trending_hist["totals"]["ever_trending_in_paper_window"],
        "p_of_campaign_trending": trending_hist["totals"]["p_of_campaign"],
        "survival": {"flagged": survival["flagged"], "control": survival["control"]},
    },
    "series": ref["series"],
    "flame": flame,
    "timeline": [{k: r[k] for k in
                  ("id", "name", "alive", "cat", "n_stars", "n_fake", "p_fake",
                   "trending", "months")} for r in timeline],
    # Ranked table: the whole set is 18.6k rows, which no reader scrolls and
    # would triple the page. Biggest campaigns by fake-star count.
    "table": [{k: r[k] for k in
               ("id", "name", "alive", "cat", "n_stars", "n_fake", "p_fake",
                "trending", "packages", "stars_now")}
              for r in sorted(repos, key=lambda r: -r["n_fake"])[:600]],
    "cat_totals": [{"cat": c, "repos": n,
                    "stars": sum(r["n_stars"] for r in repos if r["cat"] == c),
                    "fake": sum(r["n_fake"] for r in repos if r["cat"] == c),
                    "gone": sum(1 for r in repos if r["cat"] == c and r["alive"] is False),
                    "trending": sum(1 for r in repos if r["cat"] == c and r["trending"])}
                   for c, n in Counter(r["cat"] for r in repos).most_common()],
    "trending_series": trending_hist["series"],
    "trending_matched": [{
        "id": id_of.get(m["repo"]),
        "name": m["repo"] if alive_of.get(m["repo"]) is False else None,
        "first": m["first_trending"], "p_fake": m["p_fake"],
        "n_stars": m["n_stars"], "n_fake": m["n_fake"],
        "cat": categorise(m["repo"], m["domain"]),
        "alive": alive_of.get(m["repo"]),
    } for m in trending_hist["matched"]],
    "blackout": blackout,
    "now": trending_now,
}

json.dump(out, open(D + "site_data.json", "w"), ensure_ascii=False)
size = Path(D + "site_data.json").stat().st_size
print(f"site_data.json  {size/1e6:.1f} MB", file=sys.stderr)
print(f"repos {len(repos)}  named {sum(1 for r in repos if r['name'])}  "
      f"withheld {sum(1 for r in repos if not r['name'])}", file=sys.stderr)
print("categories:", Counter(r["cat"] for r in repos).most_common(), file=sys.stderr)
