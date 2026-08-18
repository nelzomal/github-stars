"""Recompute every number quoted in README.md, straight from data/.

If a figure appears in the README and not here, it has no source.
"""
from pathlib import Path

D = str(Path(__file__).resolve().parents[2] / "data") + "/"
import json
from collections import Counter

ref = json.load(open(D + "reference.json"))
sv = json.load(open(D + "survival.json"))
bl = json.load(open(D + "blackout.json"))
th = json.load(open(D + "trending_hist.json"))
tn = json.load(open(D + "trending_now.json"))
site = json.load(open(D + "site_data.json"))


def h(title):
    print(f"\n\033[1m{title}\033[0m")


h("复现 StarScout（校验管线是否正确）")
print(f"  被标记的仓库          {ref['totals']['repos_flagged']:>8,}   论文 26,254")
print(f"  有刷星行动的仓库      {ref['totals']['repos_with_campaign']:>8,}   论文 18,617")
print(f"  人工编码的仓库        {ref['totals']['labelled']:>8,}   论文 580")
peak_m = max((s for s in ref["series"] if s["p_repos"]), key=lambda s: s["p_repos"])
print(f"  月度峰值占比          {peak_m['p_repos']:>8.2%}   论文 16.66% ({peak_m['month']})")
print(f"    = {peak_m['anomalous_repos']}/{peak_m['popular_repos']} 个当月拿到 ≥50 星的仓库")

h("热榜（两个方向）")
t = th["totals"]
print(f"  刷星仓库里上过热榜的  {t['ever_trending']:>8,}   = {t['p_of_campaign']:.2%} 的刷星仓库")
print(f"    其中落在检测窗口内  {t['ever_trending_in_paper_window']:>8,}   论文 78 (0.42%)")
series = [s for s in th["series"] if s["flagged_repos"]]
pk = max(series, key=lambda s: s["p_flagged"])
print(f"  热榜仓库里在刷星的    {pk['p_flagged']:>8.2%}   峰值 {pk['month']}"
      f" ({pk['flagged_repos']}/{pk['trending_repos']})")
win = [s for s in series if s["month"] <= ref["source"]["window"][1]]
print(f"    检测窗口内月均      {sum(s['p_flagged'] for s in win)/len(win):>8.2%}")
print(f"  热榜归档覆盖          {th['archive']['days']:,} 天，{th['archive']['from']} → {th['archive']['to']}")
print(f"    语言榜              {', '.join(th['series'][-1]['languages'])}")
print("  上过热榜的仓库类别    " + ", ".join(
    f"{k} {v}" for k, v in Counter(m["cat"] for m in site["trending_matched"]).most_common()))

h("存活（我今天测的）")
for k, zh in (("flagged", "刷星仓库"), ("control", "同月份对照组")):
    s = sv[k]
    print(f"  {zh:<14}{s['gone']:>7,}/{s['alive']+s['gone']:,} 已消失 = {s['gone_pct']:.2%}"
          f"   （在线 {s['alive']:,}，其中改过名 {s['renamed']}，归档 {s['archived']}）")
print(f"  论文 2025-01 时测得    90.42%（对照 5.03%）")
print(f"  测量时间              {sv['checked_at']}")

h("两条通道（我今天测的）")
L = bl["live"]
print(f"  REST stargazers 未登录  {L['rest_anon']['status']}  {L['rest_anon']['message']}")
print(f"  REST stargazers 已登录  {L['rest_auth']['status']}  {L['rest_auth']['message']}")
print(f"  网页版 /stargazers      {L['html']['status']}")
print(f"  GraphQL stargazers      返回 {L['graphql']['edges_returned']} 条"
      f"{'，且整个查询报错' if L['graphql']['errors'] else ''}")
tl = L["public_timeline"]
print(f"  GitHub 公开事件时间线   {tl['events']} 条事件，WatchEvent"
      f" {tl['by_type'].get('WatchEvent', 0)} 条 = {tl['p_watch']:.2%}")

h("GH Archive 星标事件塌陷（我今天测的）")
print(f"  每月抽 1 天，每天抽 {len(bl['hours_per_day'])} 个整点，各读前 {bl['prefix_mb']} MB")
for a in bl["archive"]:
    if a["p_watch"] is None:
        continue
    if a["day"][5:7] in ("01", "07") or a["day"] >= "2026-01":
        print(f"    {a['day'][:7]}  WatchEvent {a['p_watch']:>7.3%}   ForkEvent {a['p_fork']:>6.3%}"
              f"   PushEvent {a['p_push']:>6.2%}   ({a['events']:,} 条)")

h("今日热榜 × 还能查的信号（我今天测的）")
rows = tn["repos"]
pages = [p["n_rows"] for p in tn["pages"] if p["n_rows"]]
print(f"  抓取                  {len(tn['pages'])} 个榜单（语言 × 日/周/月），"
      f"每榜 {min(pages)}–{max(pages)} 条")
print(f"  去重后仓库            {len(rows):,}")


def med(key):
    v = sorted(r[key] for r in rows if r.get(key) is not None)
    return v[len(v) // 2] if v else None


print(f"  fork:star 中位数      {med('fork_star'):.3f}")
print(f"  星/贡献者 中位数      {med('stars_per_contributor'):,.0f}")
print(f"  仓库年龄 中位数       {med('age_days'):,.0f} 天")
lo = sorted([r for r in rows if r["fork_star"] is not None],
            key=lambda r: r["fork_star"])[:5]
print("  fork:star 最低的五个：")
for r in lo:
    print(f"    {r['fork_star']:.4f}  {r['repo'][:40]:<40} {r['stars']:>7,} 星"
          f"  {r['contributors']:>4} 贡献者  {round(r['age_days']):>5} 天")

h("页面")
print(f"  写出名字的仓库        {sum(1 for r in site['table'] if r['name']):,} / {len(site['table']):,}（榜单内）")
print(f"  隐去名字的            {sum(1 for r in site['table'] if not r['name']):,}")
print(f"  火焰图分组            " + ", ".join(f"{g['n']} {g['repos']:,}" for g in site["flame"]))
