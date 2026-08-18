from pathlib import Path

D = str(Path(__file__).resolve().parents[1] / "data") + "/"
PAGE = str(Path(__file__).resolve().parents[1] / "index.html")
import json

DATA = open(D + "site_data.json").read().replace("</", "<\\/")
d = json.loads(open(D + "site_data.json").read())

T = d["totals"]
SV = T["survival"]
BL = d["blackout"]
LV = BL["live"]

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>买星是真的，热榜基本没被买穿 —— 但从 2026 年起没人能再核查了</title>
<style>
  :root {
    --bg:#0e1116; --panel:#161b22; --line:#272e38; --ink:#e6edf3; --dim:#8b949e;
    --real:#2ea043; --fake:#cf3c33; --warn:#d29922; --gone:#6e4b3a; --blue:#6cb6ff;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; background:var(--bg); color:var(--ink);
    font:14px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Segoe UI",Helvetica,sans-serif;
  }
  .wrap { max-width:1240px; margin:0 auto; padding:28px 22px 90px; }
  h1 { font-size:23px; margin:0 0 6px; letter-spacing:-.01em; }
  h2 { font-size:18px; margin:52px 0 4px; letter-spacing:-.01em; }
  h2 .no { color:#3d4757; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
           font-size:15px; margin-right:9px; }
  .sub { color:var(--dim); margin:0 0 22px; max-width:80ch; }
  .sub b, .note b { color:var(--ink); font-weight:600; }
  .note { color:var(--dim); margin:0 0 16px; max-width:82ch; }
  code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.92em;
         background:#1c222b; padding:1px 5px; border-radius:4px; }
  a { color:var(--blue); }

  pre.funnel { background:var(--panel); border:1px solid var(--line); border-radius:9px;
       padding:16px 18px; overflow-x:auto; font-size:13px; line-height:1.85;
       font-family:ui-monospace,SFMono-Regular,Menlo,monospace; color:#c3ccd6; margin:0 0 8px; }
  pre.funnel b { color:var(--ink); }
  pre.funnel i { color:var(--fake); font-style:normal; }
  pre.funnel u { color:var(--real); text-decoration:none; }

  .bar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:14px 0; }
  .seg { display:flex; border:1px solid var(--line); border-radius:7px; overflow:hidden; }
  .seg button { background:transparent; border:0; color:var(--dim); padding:7px 13px;
    cursor:pointer; font:inherit; font-size:13px; border-right:1px solid var(--line); }
  .seg button:last-child { border-right:0; }
  .seg button.on { background:#22303f; color:var(--ink); }
  .seg button:hover:not(.on) { background:#1b222c; color:var(--ink); }
  input[type=search] { background:var(--panel); border:1px solid var(--line); border-radius:7px;
    color:var(--ink); padding:7px 11px; font:inherit; font-size:13px; width:230px; }
  input[type=search]::placeholder { color:#5b6572; }
  .ghost { background:transparent; border:1px solid var(--line); border-radius:7px;
    color:var(--dim); padding:7px 13px; font:inherit; font-size:13px; cursor:pointer; }
  .ghost:hover { color:var(--ink); border-color:#3d4757; }

  .legend { display:flex; gap:16px; flex-wrap:wrap; margin:0 0 10px; font-size:12.5px; color:var(--dim); }
  .legend span { display:flex; align-items:center; gap:6px; }
  .sw { width:11px; height:11px; border-radius:2px; display:inline-block; }

  .crumbs { font-size:12.5px; color:var(--dim); margin-bottom:8px; min-height:19px;
            font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  .crumbs a { color:var(--blue); cursor:pointer; text-decoration:none; }
  .crumbs a:hover { text-decoration:underline; }

  #flame { position:relative; border:1px solid var(--line); border-radius:9px;
           background:var(--panel); padding:8px; overflow:hidden; }
  .row { position:relative; height:27px; margin-bottom:3px; }
  .rowlabel { position:absolute; left:-1px; top:-17px; font-size:11px; color:#5b6572; }
  .cell { position:absolute; top:0; height:27px; border-radius:3px; cursor:pointer;
    overflow:hidden; white-space:nowrap; font-size:12px; line-height:27px; padding:0 7px;
    color:#fff; text-shadow:0 1px 2px rgba(0,0,0,.55); border:1px solid rgba(0,0,0,.35);
    transition:filter .08s, opacity .08s; }
  .cell:hover { filter:brightness(1.28); }
  .cell.anc { background:#2b3441 !important; color:var(--dim); text-shadow:none; }
  .cell.dim { opacity:.17; }
  .cell.hit { outline:2px solid var(--blue); outline-offset:-2px; }
  .cell .pct { color:rgba(255,255,255,.62); font-size:11px; margin-left:7px;
               font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }

  .detail { margin-top:18px; border:1px solid var(--line); border-radius:9px;
            background:var(--panel); padding:16px 18px; min-height:132px; }
  .detail h3 { margin:0 0 3px; font-size:15px; word-break:break-all; }
  .detail .kind { font-size:11.5px; color:var(--dim); }
  .kv { display:grid; grid-template-columns:max-content 1fr; gap:3px 16px; font-size:13px; margin-top:11px; }
  .kv dt { color:var(--dim); }
  .kv dd { margin:0; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; word-break:break-all; }
  .mixbar { height:9px; border-radius:5px; overflow:hidden; display:flex; margin:11px 0 5px; background:#22272e; }
  .mixbar i { display:block; height:100%; }

  table { border-collapse:collapse; width:100%; margin:0 0 10px; font-size:13px; }
  th,td { text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }
  th { color:var(--dim); font-weight:500; font-size:12px; white-space:nowrap; }
  th.s { cursor:pointer; user-select:none; }
  th.s:hover { color:var(--ink); }
  th.s.on { color:var(--ink); }
  td.num, th.num { text-align:right; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  th.num { font-family:inherit; }
  tr:hover td { background:#1b222c; }
  td.name { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; word-break:break-all; }
  td.held { color:#5b6572; font-style:normal; }
  .caption { color:var(--dim); font-size:12.5px; margin:9px 0 0; max-width:84ch; }
  .scroll { max-height:520px; overflow-y:auto; border:1px solid var(--line);
            border-radius:9px; background:var(--panel); }
  .scroll table { margin:0; }
  .scroll thead th { position:sticky; top:0; background:#1b212a; z-index:1; }

  /* month grid */
  .grid { border:1px solid var(--line); border-radius:9px; background:var(--panel);
          padding:12px 14px; overflow-x:auto; }
  .grow { display:flex; align-items:center; gap:9px; margin-bottom:2px; }
  .glabel { flex:0 0 210px; font-size:11.5px; color:var(--dim); white-space:nowrap;
            overflow:hidden; text-overflow:ellipsis;
            font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  .gcells { flex:1; display:flex; gap:1px; min-width:520px; }
  .gc { flex:1; height:17px; border-radius:1px; background:#1c222b; position:relative; cursor:pointer; }
  .gc:hover { outline:1px solid var(--blue); }
  .gaxis { display:flex; gap:1px; margin-top:5px; min-width:520px; }
  .gaxis span { flex:1; font-size:9px; color:#4a5462; text-align:center;
                font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }

  /* line chart */
  .chart { border:1px solid var(--line); border-radius:9px; background:var(--panel); padding:14px; }
  .chart svg { display:block; width:100%; height:260px; }

  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(255px,1fr)); gap:12px; margin:14px 0 6px; }
  .card { border:1px solid var(--line); border-radius:9px; background:var(--panel); padding:13px 15px; }
  .card h4 { margin:0 0 8px; font-size:13px; color:var(--dim); font-weight:500; }
  .card .big { font-size:19px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  .card .big.bad { color:var(--fake); }
  .card .big.ok { color:var(--real); }
  .card p { margin:7px 0 0; font-size:12px; color:var(--dim); line-height:1.6; }
  .card code { font-size:11px; }

  .callout { margin-top:20px; border:1px solid #4a2320; border-left:3px solid var(--fake);
             border-radius:9px; background:#1a1315; padding:15px 18px; }
  .callout h4 { margin:0 0 7px; font-size:14.5px; color:#ff8b80; }
  .callout p { margin:0 0 9px; color:#c3ccd6; max-width:84ch; }
  .callout p:last-child { margin-bottom:0; }
  .foot { margin-top:60px; padding-top:18px; border-top:1px solid var(--line);
          color:var(--dim); font-size:12.5px; max-width:84ch; }
  .foot p { margin:0 0 9px; }
</style>
</head>
<body>
<div class="wrap">

<h1>买星是真的，热榜基本没被买穿 —— 但从 2026 年起，没人能再核查了</h1>
<p class="sub">
  <b>__CAMPAIGN__</b> 个仓库被判定买过星，这是产业规模。但把分母换成「实际出现在
  GitHub 热榜上的仓库」，被渗透的比例月度峰值只有 <b>__PEAK_TRENDING_SHORT__</b> ——
  热榜的排序算法把绝大部分刷出来的热度挡在了外面。
  这两个数来自 ICSE'26 论文的公开复现包，本页用标准库重算了一遍；
  而<b>存活状态、热榜分母、以及下面第 6 节那两条已经关掉的核查通道</b>，
  是 <b>__TODAY__</b> 现场测的。
</p>

<pre class="funnel">__FUNNEL__</pre>
<p class="caption">
  横向的比例（<b>刷星仓库里有多少上过热榜</b>）是论文报的 0.42%，我独立复算是
  __P_CAMPAIGN__。但真正该问的是纵向的比例 —— <b>热榜仓库里有多少在刷星</b> ——
  论文没给，见第 5 节：月度峰值 <b>__PEAK_TRENDING__</b>。
</p>

<h2><span class="no">01</span>这些星星买在了什么项目上</h2>
<p class="note">
  第一层是<b>今天这个仓库还在不在 GitHub 上</b>（我今天挨个查的），
  第二层是项目类别，第三层是单个仓库，第四层是月份。
  条形宽度是<b>星数</b>，颜色是<b>其中被判定为假星的比例</b> —— 越红说明这个仓库的星越是买来的。
  点任意一条可以逐层下钻。
</p>

<div class="bar">
  <div class="seg" id="metric">
    <button data-m="v" class="on">宽度 = 星数</button>
    <button data-m="f">宽度 = 假星数</button>
  </div>
  <input type="search" id="q" placeholder="高亮仓库名 / 类别…">
  <button class="ghost" id="reset">重置缩放</button>
  <span style="color:var(--dim);font-size:12.5px" id="hint"></span>
</div>

<div class="legend">
  <span><i class="sw" style="background:var(--real)"></i> 真实星标</span>
  <span><i class="sw" style="background:var(--fake)"></i> 被判定为假的星标</span>
  <span style="color:#5b6572">条形内部的红/绿分界，就是这个子树的真假配比</span>
</div>

<div class="crumbs" id="crumbs"></div>
<div id="flame"></div>
<div class="detail" id="detail"></div>

<p class="caption">
  <b>两组的浓度完全不同：</b>被 GitHub 删掉的那 __GONE_N__ 个仓库，星标的
  <b>__GONE_FAKE_PCT__</b> 是假的 —— 基本是纯刷出来的空壳；而活下来的 __ALIVE_N__ 个只有
  <b>__ALIVE_FAKE_PCT__</b>。后者是混合体：有真实项目被顺带刷了一笔，也有本来就判错的。
</p>
<p class="caption">
  <b>关于点名：</b>页面上只写出<b>已经被 GitHub 删除</b>的仓库名。
  这套检测的<b>精度无法直接评估</b> —— 没有任何办法去验证单独一颗星到底是不是买来的，
  论文自己也这么说，它退而用删除率做旁证。按论文里那句「即便有 99% 的精度」来估，
  一万八千多个里也还剩约 <b>180 个误判</b>。这个页面没法向被误判的、还活着的项目解释什么，
  所以还在线的仓库只留类别和数字，名字用编号代替。已经不存在的仓库不存在这个问题，
  而它们恰好就是恶意软件集中的地方。
</p>

<h2><span class="no">02</span>GitHub 清掉的到底是谁</h2>
<p class="note">
  上面那条「今天已经消失了」是这套检测<b>唯一的外部验证</b> ——
  GitHub 不知道这份名单存在，是它自己按自己的规则删的。
  但仓库被删可以是因为它装的东西，不一定是因为星。所以我把同一个问题往下问了一层，问到<b>账号</b>：
  取 __ACC_DAY__ 三个整点的 GH Archive，把那几小时里的每一个星标账号按
  「点没点过被标记的仓库」分成两组，再逐个查今天还在不在。
</p>

<table>
  <thead><tr><th>组</th><th class="num">数量</th><th class="num">今天已消失</th></tr></thead>
  <tbody>__ACC_TABLE__</tbody>
</table>
<p class="caption">
  账号这一组是<b>故意做弱的</b>：那几小时里点过任一被标记仓库的人全算进来了，包含大量正常用户。
  论文用后处理过的账号集在 2025-01 测得 <b>57.07%</b> 已删（基线 3.54%）—— 稀释只会让差距变小，
  这是安全的方向。口径上，GraphQL 对<b>已删除、已封禁、已改名</b>一律返回 null，
  三者从外部分不开；组织账号不能点星，所以 null 不会是组织。
</p>

<p class="note" style="margin-top:26px">
  <b>但被清掉的不是「星得多」的账号，恰恰相反。</b>下面是两组<b>幸存者</b>各自星过多少个仓库：
</p>
__ACC_DIST__
<p class="caption">
  中位数：刷星组 <b>__ACC_T_MED__</b> 个，对照组 <b>__ACC_C_MED__</b> 个。
  对照组里星得最多的那个账号星过 <b>__ACC_C_MAX__</b> 个仓库，活得好好的。
  GitHub 的 <a href="https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies"
  rel="noopener">Acceptable Use Policies</a> 确实禁止「rank abuse, such as automated starring or following」
  和「secondary markets for the purpose of the proliferation of inauthentic activity」，
  但<b>星标总数没有上限</b> —— 能卡住你的只有二级限流：每分钟 80 次、每小时 500 次内容生成请求，
  且网页上的点击也计入。被清掉的是另一种账号：没有仓库、只点过一两颗星的空壳。
</p>

<p class="note" style="margin-top:26px">
  <b>而仓库那一侧，删的理由几乎也不是星。</b>按类别拆开就看得很清楚：
</p>
<table>
  <thead><tr><th>类别</th><th class="num">仓库数</th><th class="num">今天已消失</th></tr></thead>
  <tbody>__CAT_TABLE__</tbody>
</table>
<p class="caption">
  被删掉的是恶意软件、盗版分发、外挂加载器 —— 星标是它们的<b>广告手段</b>，
  GitHub 下架的是载荷，星只是跟着一起没了。
  <b>只买星、内容本身没问题的仓库基本不会被动</b>：__TRENDING_N__ 个上过热榜的被标记仓库里，
  <b>__TR_ALIVE__ 个（__TR_ALIVE_PCT__）今天还在线</b>，而整体是 __GONE_PCT__ 已删。
</p>

<h2><span class="no">03</span>买来的星长什么样</h2>
<p class="note">
  横轴是 <b>__WINDOW__</b> 的每一个月，每一行是一个仓库，格子的<b>亮度</b>是那个月的星数、
  <b>颜色</b>是那个月的真假配比。这里放的是 <b>__TRENDING_N__</b> 个上过 GitHub 热榜的刷星仓库
  —— 真实增长是连续的浅色，买来的星是孤零零一格烧红的方块。
</p>
<div class="grid" id="grid"></div>
<p class="caption" id="gridcap">悬停任意格子看那个月的数字。</p>

<h2><span class="no">04</span>最大的那些刷星行动</h2>
<p class="note">按假星绝对数排序的前 600 个。点表头排序。</p>
<div class="bar">
  <input type="search" id="tq" placeholder="筛选仓库名 / 类别…">
  <div class="seg" id="tfilter">
    <button data-f="all" class="on">全部</button>
    <button data-f="trending">上过热榜</button>
    <button data-f="alive">仍然在线</button>
    <button data-f="gone">已被删除</button>
  </div>
  <span style="color:var(--dim);font-size:12.5px" id="thint"></span>
</div>
<div class="scroll"><table id="tbl">
  <thead><tr>
    <th class="s" data-k="name">仓库</th>
    <th class="s" data-k="cat">类别</th>
    <th class="s num" data-k="n_stars">星数</th>
    <th class="s num on" data-k="n_fake">其中假星</th>
    <th class="s num" data-k="p_fake">假星占比</th>
    <th>构成</th>
    <th class="s" data-k="trending">上过热榜</th>
    <th class="s" data-k="alive">今天还在吗</th>
  </tr></thead>
  <tbody></tbody>
</table></div>

<h2><span class="no">05</span>热榜到底被渗透到什么程度</h2>
<p class="note">
  论文说：__CAMPAIGN__ 个刷星仓库里，有 __TRENDING_N_WINDOW__ 个上过热榜，占 0.42%。
  这个方向的比例说明<b>刷星的项目大多冲不上热榜</b>，但它回答不了读者真正关心的问题。
  把同一批数据换个分母 —— 拿每个月<b>实际出现在热榜上的仓库</b>作底 ——
  得到的才是「我在热榜上看到的项目，有多大概率在刷星」。
</p>
<div class="chart" id="tchart"></div>
<p class="caption">
  纵轴是当月热榜仓库中被判定刷星的比例。峰值 <b>__PEAK_TRENDING__</b>。
  <b>2025 年之后的下降不是真的下降</b> —— StarScout 的检测窗口在 __WINDOW_END__ 结束，
  之后的月份没有任何仓库被检测过，所以那一段只是<b>没人看了</b>。
  热榜归档只覆盖 __LANGS__ 六个语言榜，不含全语言首页，所以分母也是偏小的。
</p>

<h2><span class="no">06</span>为什么这个页面往后没法更新了</h2>
<p class="note">
  上面每一个数字，追到底都依赖两样东西：<b>谁给这个仓库点了星</b>，和<b>什么时候点的</b>。
  这两样东西过去有两条公开通道可以拿到。__TODAY__ 我把两条都测了一遍。
</p>

<div class="cards">
  <div class="card">
    <h4>通道一 · 星标名单接口（未登录）</h4>
    <div class="big bad">__REST_ANON__</div>
    <p><code>GET /repos/{owner}/{repo}/stargazers</code><br>__REST_ANON_MSG__</p>
  </div>
  <div class="card">
    <h4>通道一 · 星标名单接口（已登录）</h4>
    <div class="big bad">__REST_AUTH__</div>
    <p>GitHub 2026-06-30 公告：该接口<b>只对仓库管理员和协作者开放</b>，
       对其他人返回「找不到」而不是「无权限」。</p>
  </div>
  <div class="card">
    <h4>通道一 · 网页版星标列表</h4>
    <div class="big bad">__HTML_STATUS__</div>
    <p><code>github.com/{owner}/{repo}/stargazers</code> 同步下线。
       官方理由是这些数据「被越来越多地用于收集用户信息以实施垃圾行为」。</p>
  </div>
  <div class="card">
    <h4>通道一 · GraphQL stargazers</h4>
    <div class="big bad">__GQL_EDGES__ 条</div>
    <p>论文的采集脚本用的正是这个查询。今天它<b>__GQL_STATE__</b>。</p>
  </div>
</div>

<p class="note" style="margin-top:22px">
  通道二是 <b>GH Archive</b> —— 把 GitHub 公开事件流逐小时存档、可回放的公共数据集，
  所有假星研究（包括这篇论文）都建在它上面。星标事件在里面叫 <code>WatchEvent</code>。
  我从 2019 年 7 月起每月抽一天、每天抽三个整点，量它占全部事件的比例：
</p>
<div class="chart" id="bchart"></div>
<p class="caption">
  __ARCH_2019__ → __ARCH_2025__ → <b>__ARCH_LAST__</b>。
  同期 <code>PushEvent</code> 的绝对量不降反升，说明存档本身在正常工作 ——
  塌掉的只是星标、fork、issue 这几类事件。
</p>

<div class="callout">
  <h4>但 GitHub 自己还在发星标事件</h4>
  <p>
    同一时刻我拉了 GitHub 官方的公开事件时间线 <code>GET /events</code>：
    <b>__TL_EVENTS__ 条事件里有 __TL_WATCH__ 条 WatchEvent（__TL_PCT__）</b>，
    和 2019 年的比例没有区别。
  </p>
  <p>
    所以这不是 GitHub 停发，而是<b>公共存档不再收到它们了</b>。
    差别很实际：官方接口只能看到最近几百条、翻几页就返回 422，
    存档才是能回溯七年、做统计的那一份。前者还在，后者没了。
  </p>
  <p>
    存档方自己也在追这个问题。<a href="https://github.com/igrigorik/gharchive.org/issues/320"
    rel="noopener">gharchive.org#320</a>（2026-05-14）拿 GitHub 的星标名单接口当基准去量，
    结论是 WatchEvent 捕获率从 <b>95–100% 掉到 2026 年的不足 20%</b>，
    两个拐点分别在 <b>2025 年 6 月</b>和 <b>2026 年 2 月</b> ——
    和上面这条曲线的形状一致。同一个仓库里还挂着
    <a href="https://github.com/igrigorik/gharchive.org/issues/310" rel="noopener">#310</a>
    「事件掉了 100 倍」等若干条，都还开着。采集端是按页轮询官方事件接口的，
    GitHub 的事件量涨上去之后，两次轮询之间的事件就直接丢了。
  </p>
  <p style="margin-bottom:0">
    值得记一笔的是：那个 issue 用来当基准的接口，正是
    <code>/repos/{owner}/{repo}/stargazers</code> —— 写下那份分析<b>六周之后</b>，
    GitHub 把它关掉了。于是两条通道，一条被明确关闭，一条在无人公告的情况下烂掉，
    而用来发现后者坏了的手段，恰好是前者。结果是：
    <b>2026 年之后，一个仓库的星是不是买来的，外部已经没有办法判断了。</b>
  </p>
</div>

<h2><span class="no">07</span>那现在还能看什么</h2>
<p class="note">
  星标名单没了，但仓库的其它计数还在。__TODAY__ 我把 GitHub 热榜的<b>全语言首页
  + __NOW_LANGS__ 个语言榜</b> × 日/周/月三档全抓了一遍，去重 <b>__NOW_N__</b> 个仓库，
  逐个查这些还活着的比值：<code>fork:star</code> 低说明没人真的把它拿去改，
  <code>星数/贡献者</code> 高说明关注度和参与度不成比例。
</p>
<div class="bar">
  <input type="search" id="nq" placeholder="筛选仓库 / 语言…">
  <span style="color:var(--dim);font-size:12.5px">按 fork:star 从低到高，点表头换列</span>
</div>
<div class="scroll"><table id="ntbl">
  <thead><tr>
    <th class="s" data-k="repo">仓库</th>
    <th class="s" data-k="language">语言</th>
    <th class="s num" data-k="stars">星数</th>
    <th class="s num on" data-k="fork_star">fork:star</th>
    <th class="s num" data-k="contributors">贡献者</th>
    <th class="s num" data-k="stars_per_contributor">星/贡献者</th>
    <th class="s num" data-k="commits">提交</th>
    <th class="s num" data-k="age_days">仓库年龄(天)</th>
    <th class="s num" data-k="stars_per_day">星/天</th>
  </tr></thead>
  <tbody></tbody>
</table></div>
<p class="caption" id="ncap"></p>
<p class="caption" style="margin-top:14px">
  <b>请不要把这张表读成一份嫌疑名单。</b>按 <code>fork:star</code> 升序排在最前面的，
  几乎全是口碑很好的正经项目 —— 安全扫描器、Neovim 插件、终端工具。
  原因很朴素：<b>这类东西是拿来装的，不是拿来改的</b>，没人会为了用它而 fork 一份。
  同样地，一个真正火起来的新项目，开头几周必然贡献者少、fork 少、提交少，
  和刷出来的曲线在这些比值上分不开。
  这些数字唯一的用处是<b>反过来</b>用：当一个仓库星数很高、而这几项<b>全部</b>贴地，
  同时 issue 区没有人说话、提交历史只有几十条，那就值得多看两眼 —— 
  也仅仅是多看两眼而已。星标名单没了之后，剩下的就只有这种程度的判断了。
</p>

<div class="foot" id="foot"></div>

</div>

<script>
const D = __DATA__;
const FLAME = D.flame, TL = D.timeline, TAB = D.table;
const C_REAL = '#2ea043', C_FAKE = '#cf3c33';
const ROWNAMES = ['全部', '今天还在不在', '类别', '仓库', '月份'];
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = x => (x == null ? '—' : Number(x).toLocaleString());
const pct = x => (x == null ? '—' : (x * 100).toFixed(x < 0.01 ? 2 : 1) + '%');

/* ------------------------------------------------------------------ flame */
// No `f` here on purpose: fakeOf() short-circuits on any node that has one,
// and the status nodes below carry none, so a total set here would freeze the
// root bar at whatever it said instead of summing the tree.
const ROOT = { n: '全部刷星仓库', v: FLAME.reduce((s, x) => s + x.v, 0), c: FLAME };
let metric = 'v', focus = ROOT, path = [ROOT], query = '';
const val = n => metric === 'v' ? n.v : fakeOf(n);

/* Every bar is painted as its own real/fake split, so a parent already shows
   what its children are made of before you click. */
const _fake = new WeakMap();
function fakeOf(n) {
  if (n.f != null) return n.f;
  if (!n.c) return 0;
  let v = _fake.get(n);
  if (v === undefined) {
    v = n.c.reduce((s, ch) => s + fakeOf(ch), 0);
    _fake.set(n, v);
  }
  return v;
}
function paint(n) {
  const tot = n.v || 1, f = Math.min(fakeOf(n), tot), p = f / tot * 100;
  if (p <= 0.2) return C_REAL;
  if (p >= 99.8) return C_FAKE;
  return `linear-gradient(90deg, ${C_FAKE} 0%, ${C_FAKE} ${p.toFixed(2)}%, ${C_REAL} ${p.toFixed(2)}%, ${C_REAL} 100%)`;
}

function layout() {
  const rows = [];
  path.slice(0, -1).forEach((a, dd) => rows.push([{ node: a, x: 0, w: 100, anc: true, depth: dd }]));
  const base = path.length - 1;
  (function walk(n, x, w, dd) {
    (rows[dd] = rows[dd] || []).push({ node: n, x, w, anc: false, depth: dd });
    if (!n.c) return;
    const tot = val(n);
    if (!tot) return;
    let at = x;
    for (const ch of n.c) {
      const cw = val(ch) / tot * w;
      if (cw > 0) walk(ch, at, cw, dd + 1);
      at += cw;
    }
  })(focus, 0, 100, base);
  return rows;
}

function renderFlame() {
  const rows = layout(), el = document.getElementById('flame');
  el.innerHTML = '';
  const q = query.trim().toLowerCase();
  let hits = 0;
  rows.forEach((cells, dd) => {
    const row = document.createElement('div');
    row.className = 'row';
    if (ROWNAMES[dd]) row.innerHTML = `<span class="rowlabel">${ROWNAMES[dd]}</span>`;
    row.style.marginTop = ROWNAMES[dd] ? '20px' : '';
    for (const c of cells) {
      const n = c.node, div = document.createElement('div');
      div.className = 'cell' + (c.anc ? ' anc' : '');
      div.style.left = c.x + '%';
      div.style.width = 'calc(' + c.w + '% - 2px)';
      if (!c.anc) div.style.background = paint(n);
      const share = val(n) / (val(focus) || 1) * 100;
      div.innerHTML = c.w > 4
        ? `${esc(n.n)}<span class="pct">${share >= 99.95 ? '100' : share.toFixed(1)}%</span>`
        : (c.w > 1.2 ? esc(n.n) : '');
      if (q) {
        if (n.n.toLowerCase().includes(q)) { div.classList.add('hit'); hits++; }
        else div.classList.add('dim');
      }
      div.onmouseenter = () => detail(n);
      div.onclick = () => zoom(n, c.depth);
      row.appendChild(div);
    }
    el.appendChild(row);
  });
  document.getElementById('hint').textContent = q
    ? `匹配 ${hits} 项`
    : `当前视图内 ${fmt(val(focus))} ${metric === 'v' ? '颗星' : '颗假星'}`;
  document.getElementById('crumbs').innerHTML = path.map((n, i) =>
    i === path.length - 1 ? `<span>${esc(n.n)}</span>`
      : `<a data-i="${i}">${esc(n.n)}</a>`).join(' <span style="color:#3d4757">▸</span> ');
  document.querySelectorAll('.crumbs a').forEach(a => a.onclick = () => {
    path = path.slice(0, +a.dataset.i + 1); focus = path[path.length - 1];
    renderFlame(); detail(focus);
  });
}

function detail(n) {
  const el = document.getElementById('detail');
  const f = fakeOf(n), p = n.v ? f / n.v : 0;
  const kind = n === ROOT ? '全部'
              : n.id != null ? (n.alive === false ? '仓库 · 已被 GitHub 删除'
                : n.alive === true ? '仓库 · 仍然在线（按惯例不点名）' : '仓库')
              : n.rest != null ? '该类别剩下的长尾'
              : (n.repos != null ? '分组 / 类别' : '月份');
  let rows = `<dt>星数</dt><dd>${fmt(n.v)}</dd>
              <dt>其中假星</dt><dd>${fmt(f)}（${pct(p)}）</dd>`;
  if (n.repos != null) rows += `<dt>仓库数</dt><dd>${fmt(n.repos)}</dd>`;
  if (n.t) rows += `<dt>上过热榜</dt><dd>${esc(n.t)}</dd>`;
  if (n.id != null) rows += `<dt>页面编号</dt><dd>#${n.id}</dd>`;
  el.innerHTML = `<h3>${esc(n.n)}</h3><div class="kind">${kind}</div>
    <div class="mixbar"><i style="width:${(p * 100).toFixed(2)}%;background:${C_FAKE}"></i>
    <i style="width:${(100 - p * 100).toFixed(2)}%;background:${C_REAL}"></i></div>
    <dl class="kv">${rows}</dl>`;
}

function zoom(n, depth) {
  if (n === focus) {
    if (path.length > 1) { path.pop(); focus = path[path.length - 1]; }
  } else if (depth < path.length - 1) {
    path = path.slice(0, depth + 1); focus = path[path.length - 1];
  } else {
    const chain = [];
    (function find(cur, acc) {
      acc = acc.concat([cur]);
      if (cur === n) { chain.push(...acc); return true; }
      return (cur.c || []).some(ch => find(ch, acc));
    })(ROOT, []);
    if (chain.length) { path = chain; focus = n; }
  }
  renderFlame(); detail(focus);
}

document.querySelectorAll('#metric button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#metric button').forEach(x => x.classList.remove('on'));
  b.classList.add('on'); metric = b.dataset.m; renderFlame();
});
document.getElementById('q').oninput = e => { query = e.target.value; renderFlame(); };
document.getElementById('reset').onclick = () => {
  focus = ROOT; path = [ROOT]; renderFlame(); detail(ROOT);
};
renderFlame(); detail(ROOT);

/* --------------------------------------------------------------- month grid */
const MONTHS = (() => {
  const [a, b] = D.meta.window, out = [];
  let [y, m] = a.split('-').map(Number);
  const [ey, em] = b.split('-').map(Number);
  while (y < ey || (y === ey && m <= em)) {
    out.push(`${y}-${String(m).padStart(2, '0')}`);
    m === 12 ? (y++, m = 1) : m++;
  }
  return out;
})();

(function grid() {
  const el = document.getElementById('grid'), cap = document.getElementById('gridcap');
  el.innerHTML = '';
  for (const r of TL) {
    const by = {}; let max = 1;
    for (const [mo, s, f] of r.months) { by[mo] = [s, f]; if (s > max) max = s; }
    const cells = MONTHS.map(mo => {
      const v = by[mo];
      if (!v) return `<div class="gc" data-t="${mo} · 无星标"></div>`;
      const [s, f] = v, p = s ? f / s : 0;
      // brightness carries volume, hue carries the real/fake split
      const a = 0.20 + 0.80 * Math.sqrt(s / max);
      const col = p > 0.5 ? C_FAKE : C_REAL;
      return `<div class="gc" style="background:${col};opacity:${a.toFixed(2)}"
        data-t="${mo} · ${s} 颗星，其中 ${f} 颗假（${(p * 100).toFixed(0)}%）"></div>`;
    }).join('');
    const label = r.name ? r.name : `（仍在线 #${r.id}）`;
    el.insertAdjacentHTML('beforeend',
      `<div class="grow"><div class="glabel" title="${esc(label)}">${esc(label)}</div>
       <div class="gcells">${cells}</div></div>`);
  }
  const axis = MONTHS.map(mo => `<span>${mo.endsWith('-01') ? mo.slice(2, 4) : ''}</span>`).join('');
  el.insertAdjacentHTML('beforeend',
    `<div class="grow"><div class="glabel"></div><div class="gaxis">${axis}</div></div>`);
  el.onmouseover = e => {
    if (e.target.classList.contains('gc')) cap.textContent = e.target.dataset.t;
  };
})();

/* -------------------------------------------------------------- ranked table */
let tsort = 'n_fake', tdir = -1, tfilter = 'all', tquery = '';
function renderTable() {
  let rows = TAB.slice();
  if (tfilter === 'trending') rows = rows.filter(r => r.trending);
  if (tfilter === 'alive') rows = rows.filter(r => r.alive === true);
  if (tfilter === 'gone') rows = rows.filter(r => r.alive === false);
  const q = tquery.trim().toLowerCase();
  if (q) rows = rows.filter(r => ((r.name || '') + ' ' + r.cat).toLowerCase().includes(q));
  rows.sort((a, b) => {
    const x = a[tsort], y = b[tsort];
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return (typeof x === 'string' ? x.localeCompare(y) : x - y) * tdir;
  });
  document.querySelector('#tbl tbody').innerHTML = rows.map(r => {
    const p = (r.p_fake * 100).toFixed(1);
    const name = r.name
      ? `<a href="https://github.com/${esc(r.name)}" rel="nofollow noopener">${esc(r.name)}</a>`
      : `<span class="held">（仍在线 #${r.id}，不点名）</span>`;
    return `<tr>
      <td class="name">${name}</td>
      <td>${esc(r.cat)}</td>
      <td class="num">${fmt(r.n_stars)}</td>
      <td class="num">${fmt(r.n_fake)}</td>
      <td class="num">${p}%</td>
      <td><div class="mixbar" style="margin:0;width:110px">
        <i style="width:${p}%;background:${C_FAKE}"></i>
        <i style="width:${100 - p}%;background:${C_REAL}"></i></div></td>
      <td>${r.trending ? esc(r.trending) : '<span style="color:#4a5462">—</span>'}</td>
      <td>${r.alive === false ? '<span style="color:var(--fake)">已删除</span>'
           : r.alive === true ? '<span style="color:var(--dim)">在线</span>' : '—'}</td>
    </tr>`;
  }).join('');
  document.getElementById('thint').textContent = `${rows.length} 行`;
}
document.querySelectorAll('#tbl th.s').forEach(th => th.onclick = () => {
  const k = th.dataset.k;
  if (k === tsort) tdir = -tdir; else { tsort = k; tdir = -1; }
  document.querySelectorAll('#tbl th.s').forEach(x => x.classList.remove('on'));
  th.classList.add('on');
  renderTable();
});
document.getElementById('tq').oninput = e => { tquery = e.target.value; renderTable(); };
document.querySelectorAll('#tfilter button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#tfilter button').forEach(x => x.classList.remove('on'));
  b.classList.add('on'); tfilter = b.dataset.f; renderTable();
});
renderTable();

/* ------------------------------------------------------------------- charts */
function lineChart(el, pts, opts) {
  const W = 1000, H = 240, L = 52, R = 14, TOP = 14, B = 30;
  const ys = pts.map(p => p.y).filter(v => v != null);
  const ymax = opts.ymax != null ? opts.ymax : Math.max(...ys) * 1.12;
  const x = i => L + i * (W - L - R) / Math.max(pts.length - 1, 1);
  const y = v => TOP + (1 - v / ymax) * (H - TOP - B);
  let dd = '', started = false;
  pts.forEach((p, i) => {
    if (p.y == null) { started = false; return; }
    dd += (started ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(p.y).toFixed(1) + ' ';
    started = true;
  });
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(t => {
    const v = ymax * t;
    return `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#272e38"/>
            <text x="${L - 8}" y="${y(v) + 4}" fill="#5b6572" font-size="11" text-anchor="end">${opts.fmtY(v)}</text>`;
  }).join('');
  const labels = pts.map((p, i) => (opts.labelEvery(p, i)
    ? `<text x="${x(i)}" y="${H - 9}" fill="#5b6572" font-size="10" text-anchor="middle">${p.label}</text>` : '')).join('');
  const dots = pts.map((p, i) => p.y == null ? '' :
    `<circle cx="${x(i)}" cy="${y(p.y)}" r="2.6" fill="${opts.color}"><title>${p.title}</title></circle>`).join('');
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    ${ticks}<path d="${dd}" fill="none" stroke="${opts.color}" stroke-width="2"/>${dots}${labels}</svg>`;
}

lineChart(document.getElementById('tchart'),
  D.trending_series.filter(s => s.month >= '2019-07').map(s => ({
    y: s.p_flagged, label: s.month.slice(0, 4),
    title: `${s.month}: ${s.flagged_repos}/${s.trending_repos} = ${(s.p_flagged * 100).toFixed(2)}%`,
  })), {
  color: C_FAKE, fmtY: v => (v * 100).toFixed(1) + '%',
  labelEvery: (p, i) => p.label && i % 12 === 0,
});

lineChart(document.getElementById('bchart'),
  D.blackout.archive.map(a => ({
    y: a.p_watch, label: a.day.slice(0, 4),
    title: `${a.day}: WatchEvent 占 ${(a.p_watch * 100).toFixed(2)}%（${a.events} 条事件）`,
  })), {
  color: '#6cb6ff', fmtY: v => (v * 100).toFixed(0) + '%',
  labelEvery: (p, i) => i % 12 === 0,
});

/* --------------------------------------------------- today's trending table */
let nsort = 'fork_star', ndir = 1, nquery = '';
function renderNow() {
  let rows = D.now.repos.slice();
  const q = nquery.trim().toLowerCase();
  if (q) rows = rows.filter(r => (r.repo + ' ' + (r.language || '')).toLowerCase().includes(q));
  rows.sort((a, b) => {
    const x = a[nsort], y = b[nsort];
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return (typeof x === 'string' ? x.localeCompare(y) : x - y) * ndir;
  });
  document.querySelector('#ntbl tbody').innerHTML = rows.slice(0, 400).map(r => `<tr>
    <td class="name"><a href="https://github.com/${esc(r.repo)}" rel="nofollow noopener">${esc(r.repo)}</a></td>
    <td>${esc(r.language || '—')}</td>
    <td class="num">${fmt(r.stars)}</td>
    <td class="num">${r.fork_star == null ? '—' : r.fork_star.toFixed(3)}</td>
    <td class="num">${fmt(r.contributors)}</td>
    <td class="num">${fmt(r.stars_per_contributor)}</td>
    <td class="num">${fmt(r.commits)}</td>
    <td class="num">${fmt(Math.round(r.age_days))}</td>
    <td class="num">${fmt(r.stars_per_day)}</td>
  </tr>`).join('');
  document.getElementById('ncap').textContent =
    `${rows.length} 个仓库${rows.length > 400 ? '（显示前 400）' : ''}。` +
    `fork:star 中位数 ${median(rows.map(r => r.fork_star))}，` +
    `星/贡献者中位数 ${median(rows.map(r => r.stars_per_contributor))}。`;
}
function median(xs) {
  const v = xs.filter(x => x != null).sort((a, b) => a - b);
  if (!v.length) return '—';
  const m = v[Math.floor(v.length / 2)];
  return m < 10 ? m.toFixed(3) : Math.round(m).toLocaleString();
}
document.querySelectorAll('#ntbl th.s').forEach(th => th.onclick = () => {
  const k = th.dataset.k;
  if (k === nsort) ndir = -ndir; else { nsort = k; ndir = k === 'repo' || k === 'language' ? 1 : -1; }
  document.querySelectorAll('#ntbl th.s').forEach(x => x.classList.remove('on'));
  th.classList.add('on');
  renderNow();
});
document.getElementById('nq').oninput = e => { nquery = e.target.value; renderNow(); };
renderNow();

document.getElementById('foot').innerHTML = __FOOT__;
</script>
</body>
</html>
"""


def n(x):
    return f"{x:,}"


meta = d["meta"]
today = meta["built_at"][:10]
window = meta["window"]
series_t = [s for s in d["trending_series"] if s["flagged_repos"]]
peak = max(series_t, key=lambda s: s["p_flagged"])
arch = {a["day"][:7]: a for a in BL["archive"]}
arch_last = BL["archive"][-1]
arch_2019 = BL["archive"][0]
arch_2025 = arch.get("2025-08") or BL["archive"][-13]
tl = LV["public_timeline"]
gone_grp = next(g for g in d["flame"] if "删除" in g["n"])
alive_grp = next(g for g in d["flame"] if "在线" in g["n"])

AC = d["accounts"]
acc_rows = "".join(
    f'<tr><td>{label}</td><td class="num">{n(g["n"])}</td>'
    f'<td class="num" style="color:var(--fake)">{g["gone_pct"]:.2%}</td></tr>'
    for label, g in [
        ("被判定刷星的仓库", SV["flagged"]), ("同月份对照组（仓库）", SV["control"]),
        ("点过被标记仓库的账号", AC["treatment"]), ("同小时对照组（账号）", AC["control"]),
    ])

# One bar per group, seven buckets from "starred nothing" to "starred 10k+".
# Red at the empty end, green at the busy end -- the two groups fill it from
# opposite sides, which is the entire finding.
BUCKET_COLOR = ["#cf3c33", "#d1553f", "#c07b3a", "#9c8f38", "#6d9440", "#3f9a41", "#2ea043"]


def dist_bar(group, label):
    # The label goes *inside* its own segment: a separate evenly-spaced tick row
    # would sit under the wrong bucket, since the segments are proportional.
    segs = "".join(
        f'<i style="width:{share*100:.4f}%;background:{BUCKET_COLOR[i]};'
        f'font-size:10px;line-height:15px;text-align:center;color:#0e1116;'
        f'font-family:ui-monospace,Menlo,monospace;overflow:hidden" '
        f'title="星过 {name} 个仓库：{share:.1%}">{name if share >= 0.07 else ""}</i>'
        for i, (name, share) in enumerate(group["starred_buckets"]) if share > 0)
    return (f'<div style="margin:12px 0 0"><div style="font-size:12.5px;color:var(--dim);'
            f'margin-bottom:4px">{label}（{n(group["alive"])} 个幸存账号）</div>'
            f'<div class="mixbar" style="height:15px">{segs}</div></div>')


acc_dist = ('<div style="border:1px solid var(--line);border-radius:9px;'
            'background:var(--panel);padding:13px 15px">'
            + dist_bar(AC["treatment"], "点过被标记仓库的账号")
            + dist_bar(AC["control"], "同小时对照组")
            + '<div style="font-size:11.5px;color:#5b6572;margin-top:11px">'
              '段是这个账号一共星过多少个仓库（左端一个都没星过，右端星过一万个以上），'
              '段宽是该组账号里的占比</div></div>')

cat_rows = "".join(
    f'<tr><td>{c["cat"]}</td><td class="num">{n(c["repos"])}</td>'
    f'<td class="num" style="color:var(--fake)">{c["gone"]/c["repos"]:.1%}</td></tr>'
    for c in d["cat_totals"][:8])

tr_alive = sum(1 for m in d["trending_matched"] if m["alive"] is True)

funnel = "\n".join([
    f"<i>{n(T['fake_stars']):>9}</i>  颗星标被判定为假（{window[0]} → {window[1]}）",
    f"<b>{n(T['repos_flagged']):>9}</b>  个仓库身上带着这些假星",
    f"<b>{n(T['repos_with_campaign']):>9}</b>  …其中够得上「一次刷星行动」的 ........... {T['repos_with_campaign']/T['repos_flagged']:.1%}",
    f"<i>{n(SV['flagged']['gone']):>9}</i>  …今天已经从 GitHub 上消失了 ............. {SV['flagged']['gone_pct']:.1%}",
    f"<u>{n(SV['control']['gone']):>9}</u>  （同月份、未被标记的对照组，消失了这么多） {SV['control']['gone_pct']:.1%}",
    f"<b>{T['ever_trending']:>9}</b>  …上过 GitHub 热榜的 ..................... {T['p_of_campaign_trending']:.2%}",
])

foot = f"""
<p><b>数据来源。</b>前半部分（第 1、3–5 节的历史数据）来自
<a href="https://github.com/hehao98/StarScout">hehao98/StarScout</a> 的公开复现包，
即 He 等人 <i>Six Million (Suspected) Fake Stars on GitHub</i>（ICSE'26，
<a href="https://doi.org/10.1145/3744916.3764531">10.1145/3744916.3764531</a>）的检测结果。
本页用标准库重算了它的仓库/月份口径，独立得到论文的
{n(T['repos_with_campaign'])} 个刷星仓库、{n(T['fake_stars'])} 颗假星、
{T['ever_trending_in_window']} 个上过热榜、2024-07 峰值 16.66% 四个数，
作为管线正确性的校验。</p>
<p><b>我自己测的部分。</b>第 1–2 节的存活状态、第 5 节的热榜分母、第 6 节的两条通道、
第 7 节的今日热榜信号，都是 {today} 现场跑的，脚本在 <code>scripts/</code> 里。
其中「刷星仓库今天消失了 {SV['flagged']['gone_pct']:.1%}，同月份对照组只消失了
{SV['control']['gone_pct']:.1%}」是这套检测唯一的外部验证 ——
GitHub 自己把它们删掉了。</p>
<p><b>口径与边界。</b>这套检测的精度无法直接评估（没法验证单颗星是否买来的，
论文用删除率做旁证）；按论文「即便 99% 精度」的估法，一万八千多个里仍有约 180 个误判，
所以本页只写出已被删除的仓库名。召回率论文测过：对已知的恶意刷星活动是 81.23%（仓库）/ 75.95%（账号）。「假星」始终指
<i>被这套启发式判定为可疑</i>，不等于仓库主人买过星 ——
刷星账号也会去点正常项目的星来伪装自己。
热榜归档只覆盖 {', '.join(d['trending_series'][-1]['languages'])} 六个语言榜。
检测窗口在 {window[1]} 结束，之后的月份没有任何检测数据。</p>
<p>测量时间：{meta['blackout_measured_at']}（通道探测）、{meta['trending_measured_at']}（今日热榜）、
{meta['built_at']}（存活状态）。</p>
"""

html = (HTML
        .replace("__DATA__", DATA)
        .replace("__FOOT__", json.dumps(foot, ensure_ascii=False))
        .replace("__CAMPAIGN__", n(T["repos_with_campaign"]))
        .replace("__ACC_DAY__", AC["day"])
        .replace("__ACC_TABLE__", acc_rows)
        .replace("__ACC_DIST__", acc_dist)
        .replace("__ACC_T_MED__", n(AC["treatment"]["starred_median"]))
        .replace("__ACC_C_MED__", n(AC["control"]["starred_median"]))
        .replace("__ACC_C_MAX__", n(AC["control"]["starred_max"]))
        .replace("__CAT_TABLE__", cat_rows)
        .replace("__TR_ALIVE_PCT__", f"{tr_alive/len(d['trending_matched']):.0%}")
        .replace("__TR_ALIVE__", str(tr_alive))
        .replace("__GONE_PCT__", f"{SV['flagged']['gone_pct']:.1%}")
        .replace("__TODAY__", today)
        .replace("__FUNNEL__", funnel)
        .replace("__P_CAMPAIGN__", f"{T['p_of_campaign_trending']:.2%}")
        .replace("__PEAK_TRENDING_SHORT__", f"{peak['p_flagged']:.2%}")
        .replace("__PEAK_TRENDING__", f"{peak['p_flagged']:.2%}（{peak['month']}，{peak['flagged_repos']}/{peak['trending_repos']}）")
        .replace("__WINDOW__", f"{window[0]} → {window[1]}")
        .replace("__WINDOW_END__", window[1])
        .replace("__TRENDING_N_WINDOW__", str(T["ever_trending_in_window"]))
        .replace("__TRENDING_N__", str(T["ever_trending"]))
        .replace("__LANGS__", "、".join(d["trending_series"][-1]["languages"]))
        .replace("__REST_ANON_MSG__", f"未登录时返回 <code>{LV['rest_anon']['message']}</code>")
        .replace("__REST_ANON__", str(LV["rest_anon"]["status"]))
        .replace("__REST_AUTH__", str(LV["rest_auth"]["status"]))
        .replace("__HTML_STATUS__", str(LV["html"]["status"]))
        .replace("__GQL_EDGES__", str(LV["graphql"]["edges_returned"]))
        .replace("__GQL_STATE__", "整个查询直接报错" if LV["graphql"]["errors"] else "返回空列表")
        .replace("__ARCH_2019__", f"{arch_2019['day'][:7]} 占 {arch_2019['p_watch']:.2%}")
        .replace("__ARCH_2025__", f"{arch_2025['day'][:7]} 占 {arch_2025['p_watch']:.2%}")
        .replace("__ARCH_LAST__", f"{arch_last['day'][:7]} 只剩 {arch_last['p_watch']:.2%}")
        .replace("__TL_EVENTS__", str(tl["events"]))
        .replace("__TL_WATCH__", str(tl["by_type"].get("WatchEvent", 0)))
        .replace("__TL_PCT__", f"{tl['p_watch']:.1%}")
        .replace("__NOW_LANGS__", str(len({p["lang"] for p in d["now"]["pages"] if p["lang"]})))
        .replace("__GONE_N__", n(gone_grp["repos"]))
        .replace("__GONE_FAKE_PCT__", f"{gone_grp['f'] / gone_grp['v']:.1%}")
        .replace("__ALIVE_N__", n(alive_grp["repos"]))
        .replace("__ALIVE_FAKE_PCT__", f"{alive_grp['f'] / alive_grp['v']:.1%}")
        .replace("__NOW_N__", n(len(d["now"]["repos"]))))

open(PAGE, "w").write(html)
print(f"index.html  {len(html)/1e6:.2f} MB")
