"""Drive the page's interactions programmatically and dump the result as text,
so headless Chrome (which cannot click) still exercises the flame graph's
drill-down, both sortable tables, the month grid and the two charts.

    python3 scripts/test_render.py
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        --headless --disable-gpu --dump-dom /tmp/star_test.html
"""
from pathlib import Path

PAGE = str(Path(__file__).resolve().parents[1] / "index.html")
OUT = "/tmp/star_test.html"
h = open(PAGE).read()

harness = r"""
<script>
const log = [];
const norm = s => String(s).replace(/\s+/g, ' ').trim();
const crumbs = () => norm(document.getElementById('crumbs').innerText);
const cells = () => document.querySelectorAll('#flame .cell').length;
const hint = () => norm(document.getElementById('hint').innerText);
const detailText = () => norm(document.getElementById('detail').innerText).slice(0, 220);

log.push(['flame 初始', crumbs(), cells() + ' cells', hint()]);

const gone = ROOT.c.find(x => x.n.indexOf('删除') >= 0);
zoom(gone, 1);
log.push(['下钻 → 状态', crumbs(), cells() + ' cells', hint()]);
log.push(['该层详情', detailText()]);

const cat = gone.c[0];
zoom(cat, 2);
log.push(['下钻 → 类别', crumbs(), cells() + ' cells', hint()]);

const repo = cat.c[0];
zoom(repo, 3);
log.push(['下钻 → 仓库', crumbs(), cells() + ' cells', hint()]);
log.push(['仓库详情', detailText()]);
log.push(['该仓库有月份层', String(!!repo.c)]);

zoom(ROOT, 0);
log.push(['回到顶层', crumbs(), cells() + ' cells']);
metric = 'f'; renderFlame();
log.push(['宽度切到假星数', hint()]);
metric = 'v'; query = 'wallet'; renderFlame();
log.push(['搜索 wallet', hint()]);
query = ''; renderFlame();

// month grid
const gcells = document.querySelectorAll('#grid .gc');
const hot = [...gcells].filter(c => c.style.background.indexOf('207, 60, 51') >= 0);
log.push(['月份网格', document.querySelectorAll('#grid .grow').length + ' 行',
          gcells.length + ' 格', hot.length + ' 格以假星为主']);
log.push(['网格样例', hot.length ? hot[0].dataset.t : '(无)']);

// ranked table
log.push(['排行榜默认', document.querySelectorAll('#tbl tbody tr').length + ' 行',
          norm(document.getElementById('thint').innerText)]);
tfilter = 'trending'; renderTable();
log.push(['筛选 上过热榜', document.querySelectorAll('#tbl tbody tr').length + ' 行']);
tfilter = 'alive'; renderTable();
const held = document.querySelectorAll('#tbl tbody td.name span.held').length;
log.push(['筛选 仍然在线', document.querySelectorAll('#tbl tbody tr').length + ' 行',
          held + ' 行隐去了名字']);
log.push(['在线行是否全部隐名',
          String(held === document.querySelectorAll('#tbl tbody tr').length)]);
tfilter = 'gone'; renderTable();
const named = [...document.querySelectorAll('#tbl tbody tr')].filter(
  tr => tr.querySelector('td.name a')).length;
log.push(['筛选 已删除', document.querySelectorAll('#tbl tbody tr').length + ' 行',
          named + ' 行写出了名字']);
tsort = 'p_fake'; tdir = -1; renderTable();
log.push(['按假星占比排序，首行', norm(document.querySelector('#tbl tbody tr').innerText)]);
tfilter = 'all'; tsort = 'n_fake'; renderTable();

// charts
log.push(['热榜占比图', document.querySelectorAll('#tchart circle').length + ' 个数据点',
          document.querySelectorAll('#tchart path').length + ' 条折线']);
log.push(['事件塌陷图', document.querySelectorAll('#bchart circle').length + ' 个数据点']);
const last = document.querySelectorAll('#bchart circle');
log.push(['塌陷图末点', last.length ? norm(last[last.length - 1].querySelector('title').textContent) : '(无)']);

// today's trending
log.push(['今日热榜表', document.querySelectorAll('#ntbl tbody tr').length + ' 行',
          norm(document.getElementById('ncap').innerText)]);
log.push(['最低 fork:star', norm(document.querySelector('#ntbl tbody tr').innerText)]);
nsort = 'stars'; ndir = -1; renderNow();
log.push(['按星数排序，首行', norm(document.querySelector('#ntbl tbody tr').innerText)]);

document.body.innerHTML = '<pre id="out">' +
  log.map(r => (Array.isArray(r) ? r : [r]).filter(x => x !== '').join('  |  ')).join('\n') +
  '</pre>';
</script>
"""
open(OUT, "w").write(h.replace("</body>", harness + "</body>"))
print("wrote " + OUT)
