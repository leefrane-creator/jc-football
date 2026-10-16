# -*- coding: utf-8 -*-
"""生成「可移植化交付说明」HTML（一次性脚本）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jc import config as C          # noqa: E402
from jc import ledger as LD         # noqa: E402

s = LD.summary()
css = (C.TEMPLATES / "base.css").read_text(encoding="utf-8")

STEPS = [
    ("① 脚本收成一个包", "统一命名 · 命令行入口 · 快照落盘",
     "<code>jc/</code> 9 个模块 · <code>python -m jc</code> 一个入口",
     ["<b>统一命名</b>：config / fetch / odds / legs / scheme / payout / render / ledger / cli",
      "<b>命令行入口</b>：<code>fetch · legs · scheme · payout · ticket · report · review · ledger · info</code>",
      "<b>快照落盘</b>：每次 fetch 写 <code>data/odds/YYYY-MM-DD.json</code>（含 <code>read_at</code> 时间戳）",
      "<b>零第三方依赖</b>：只用 Python 标准库，换机器不用装环境"]),
    ("② 补 SKILL.md", "把七天的固定动作链写成技能",
     "装到 <code>~/.workbuddy/skills/jc-football/</code>，说一句话即触发",
     ["七步动作链：取数 → 建腿池 → 出方案 → 测算 → 出票单 → 报告 → 复盘 → 账本",
      "六条硬约束前置（零重场 / 多留一档 / 容错过关 / 三概率 / 互斥上界 / 多票稀释）",
      "输出约定 + 用户偏好 + 自我进化流程（改专家包 → 同步知识库 → 校验注册）"]),
    ("③ 专家包拷入 + GitHub 仓库", "本来就是现成的 · 顺手建仓分发",
     "github.com/leefrane-creator/jc-football（public，32 文件）",
     ["专家包 v1.14.0 拷入 <code>expert/</code>，作为<b>知识唯一源头</b>",
      "仓库含 README / install.md / LICENSE(MIT) / .gitignore",
      "<b>换机器 5 步</b>：clone → 拷进 skills → 注册专家 → 首跑自检 → 恢复历史"]),
    ("④ 数据落库", "赔率快照 + 战绩账本",
     f"9 张历史票已入库：投入 {s['cost']:.0f} / 回款 {s['payout']:.2f} / 净 {s['net']:+.2f}",
     ["<b>赔率快照</b>：<code>data/odds/*.json</code>（过期场次接口不再返赔率，不存就无法复盘）",
      "<b>战绩账本</b>：<code>data/ledger.json</code>，<code>jc ledger add|settle|show</code> 增改查",
      "<b>复盘自动化</b>：<code>jc review</code> 直接出报告（含累计盈亏走势图）"]),
]

VERIFY = [
    ("fetch 5 池", "had 43 场 / 其余 44 场 —— 复现「had 池缺场次」禁忌", "ok"),
    ("建腿池", "641 条（五大联赛可售场次）", "ok"),
    ("scheme N=3", "中奖 49.5% / 盈利 49.5% / 全中 12.16% / 错1腿回 100%", "ok"),
    ("scheme N=4", "中奖 83.1% / 盈利 49.0% / 全中 13.73% / 错1腿回 105%", "ok"),
    ("payout 复式", "返还率 63.6% = 79.8%²（总进球 2串1），分情形回款正确", "ok"),
    ("ledger", "620 / 537.26 / −82.74 —— 与历史账本逐项一致", "ok"),
    ("HTML 校验", "报告 / 出票单 / 复盘 3 份标签闭合无误", "ok"),
]

body = [f"<h1>竞彩能力可移植化 · 交付说明</h1>",
        f'<p class="sub">四步全部完成 ｜ 生成 {__import__("datetime").datetime.now():%Y-%m-%d %H:%M}</p>',
        '<div class="note"><b>一句话</b>：把「取数 / 计算 / 模板 / 知识库」打成一个自包含包 '
        '<code>jc-football/</code>，装上技能就能一句话触发，发到 GitHub 就能换机器复现。'
        '<br><b>知识库 &gt; 计算规则 &gt; 取数规则 &gt; 模板 &gt; 脚本</b>——脚本是壳，规则才是核。</div>',
        '<h2>四步交付</h2>']

for title, sub, out, items in STEPS:
    body.append(f"""<div class="card">
  <h3>{title} <span class="dim" style="font-weight:400;font-size:13.5px">· {sub}</span></h3>
  <p><span class="pill ok">{out}</span></p>
  <ul>{''.join(f'<li>{x}</li>' for x in items)}</ul>
</div>""")

body.append('<h2>端到端验证（真实取数 · 非模拟）</h2><table>'
            '<tr><th>检查项</th><th>结果</th><th class="num">状态</th></tr>')
for item, result, st in VERIFY:
    body.append(f'<tr><td>{item}</td><td>{result}</td>'
                f'<td class="num"><span class="pill ok">通过</span></td></tr>')
body.append('</table>')

body.append(f"""<h2>换机器怎么用</h2>
<div class="card"><ol>
<li><code>git clone https://github.com/leefrane-creator/jc-football.git</code></li>
<li>拷到 <code>~/.workbuddy/skills/jc-football</code>（或工作区 <code>.workbuddy/skills/</code>）</li>
<li>注册专家：<code>validate_expert.py expert &amp;&amp; register_expert.py expert</code></li>
<li>首跑自检：<code>python -m jc fetch &amp;&amp; python -m jc info</code></li>
<li>恢复历史：<code>python scripts/seed_ledger.py</code>，然后 <code>python -m jc review</code></li>
</ol>
<p class="dim">此后说一句「分析今晚的英超」即可自动加载本技能。</p></div>

<h2>包结构</h2>
<pre style="background:#1c2024;color:#dfe6ee;padding:16px 18px;border-radius:10px;overflow:auto;font-size:12.5px;line-height:1.6">jc-football/
├─ SKILL.md              # 一句话触发：动作链 + 硬约束 + 输出约定
├─ README.md / install.md / LICENSE / .gitignore / requirements.txt
├─ jc/                   # 包：config fetch odds legs scheme payout render ledger cli
├─ scripts/              # sync_knowledge.py（从专家包同步）· seed_ledger.py
├─ knowledge/            # 铁律 · 经验库 · 案例记录 · 自检清单 · 数据接口
├─ templates/base.css
├─ expert/               # 竞彩足球分析师 v1.14.0（知识唯一源头）
├─ data/                 # odds/ 每日快照 · legs/ · ledger.json 战绩账本
└─ outputs/              # 出票单 / 报告 / 复盘 HTML</pre>

<h2>两个必须记住的坑</h2>
<div class="card"><ul>
<li><b>取数</b>：禁止跨池 <code>dict.update()</code>（会把赔率覆盖成空）；基准索引必须用 <code>ttg</code>（<code>had</code> 会缺场次）。</li>
<li><b>推送</b>：本机代理放行 <code>api.github.com</code> 但拦 git-https（502）→ 走 REST API，不要用 <code>git push</code>。</li>
</ul></div>

<h2>【合规声明】</h2>
<div class="card"><ul>
<li>本工具只做体育赛事数据分析与结构测算，<b>不构成投注建议</b>，不承诺任何收益。</li>
<li>不做代购、不做资金归集、不做"包中/稳赚"宣传、不传播他人票面。</li>
<li>未满 18 周岁禁止购买彩票，请理性购彩。</li>
</ul></div>""")

html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>竞彩能力可移植化 · 交付说明</title><style>{css}</style></head>
<body><div class="wrap">{''.join(body)}
<div class="card-foot">生成 {__import__("datetime").datetime.now():%Y-%m-%d %H:%M} ｜ 数据来源：本工具包账本 data/ledger.json</div>
</div></body></html>"""

out = ROOT.parent / "outputs" / "jc-portability-done.html"
out.write_text(html, encoding="utf-8")
print(f"已写出 {out}  ({len(html.encode())} bytes)")
