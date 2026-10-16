# -*- coding: utf-8 -*-
"""HTML 渲染：出票单（仿彩票 APP 购买详情页）、分析报告、复盘报告。

统一自包含（内联样式），可直接双击打开，也可上传腾讯文档 AIPage。
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from . import config as C
from . import scheme as S
from . import payout as P
from . import odds as O


def _css() -> str:
    return (C.TEMPLATES / "base.css").read_text(encoding="utf-8")


def _page(title: str, body: str, foot: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{_css()}</style></head>
<body><div class="wrap">
{body}
<div class="card-foot">{foot}</div>
</div></body></html>"""


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _pct(x: float, nd: int = 1) -> str:
    return f"{x * 100:.{nd}f}%"


# ================================================================ 出票单

def ticket_html(tickets: Sequence[dict], title: str = "竞彩足球 · 出票单",
                read_at: Optional[str] = None, note: str = "") -> str:
    """tickets: [{name, legs:[leg...], multiple, comment}]"""
    read_at = read_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    body = [f"<h1>{_e(title)}</h1>",
            f'<p class="sub">生成 {read_at} ｜ 赔率读取 {read_at} ｜ 以出票时刻官方 SP 为准</p>']
    if note:
        body.append(f'<div class="note">{note}</div>')

    alllegs: List[dict] = []
    total_bets = total_cost = 0
    for t in tickets:
        legs = [S.as_leg(L) for L in t["legs"]]
        m = S.metrics(legs, unit=C.UNIT)
        mult = int(t.get("multiple", 1))
        alllegs.extend(legs)
        total_bets += m["bets"] * mult
        total_cost += m["cost"] * mult

        rows = []
        for L in legs:
            arm = " / ".join(f"@{o:.2f}" for o in L["odds"])
            picks = " ".join(f"{o:.2f}" for o in L["odds"])
            rows.append(
                f'<div class="trow"><div class="no">{_e(L["key"])}</div>'
                f'<div><div>{_e(L["home"])} vs {_e(L["away"])}</div>'
                f'<div class="meta">{_e(L["league"])} · {_e(str(L["date"])[5:])} {_e(str(L["time"])[:5])}'
                f' {"· 让" + _e(L["line"]) if L.get("line") not in (None, "") else ""}</div></div>'
                f'<div>{_e(L["name"])}</div>'
                f'<div class="pick">{picks}</div></div>')

        body.append(f"""<div class="ticket">
  <div class="thead"><span>{_e(t.get('name', '票'))}</span>
    <span>过关方式 纯 2串1（{m['N']} 场）</span></div>
  <div class="tbody">{''.join(rows)}</div>
  <div class="tfoot">
    <span>倍数 <b>{mult}</b></span><span>注数 <b>{m['bets'] * mult}</b></span>
    <span>金额 <b>¥{m['cost'] * mult:.0f}</b></span>
    <span>全中回款 <b class="ok">¥{m['full_pay'][0]:.2f}–{m['full_pay'][1]:.2f}</b></span>
    <span>错 1 腿回款 <b class="{'ok' if m['fault_recover'] >= 1 else 'bad'}">¥{m['pay_by_hits'].get(m['N'] - 1, (0, 0))[0]:.2f}–{m['pay_by_hits'].get(m['N'] - 1, (0, 0))[1]:.2f}</b></span>
  </div>
</div>""")

    body.append(f"""<div class="kpi">
  <div class="k"><div class="v">{total_bets}</div><div class="l">合计注数</div></div>
  <div class="k"><div class="v">¥{total_cost:.0f}</div><div class="l">合计金额</div></div>
  <div class="k"><div class="v">{len(tickets)}</div><div class="l">票数</div></div>
</div>""")

    body.append("""<h2>柜台核对表</h2><table><tr><th>编号</th><th>对阵</th><th>玩法</th>
<th>选号（红字为下注项）</th><th>赔率</th></tr>""" + "".join(
        f'<tr><td>{_e(L["key"])}</td><td>{_e(L["home"])} vs {_e(L["away"])}</td>'
        f'<td>{_e(L["name"])}</td><td class="pick">{"/".join(f"{o:.2f}" for o in L["odds"])}</td>'
        f'<td class="num">{"/".join(f"{o:.2f}" for o in L["odds"])}</td></tr>'
        for L in alllegs) + "</table>")

    foot = "理性购彩 · 未满 18 周岁禁止购彩 · 本单仅为数据分析结果，不构成投注建议"
    return _page(title, "\n".join(body), foot)


# ================================================================ 分析报告

_PLAY_ROWS = [("had", "胜平负"), ("hhad", "让球胜平负"), ("crs", "比分"),
              ("ttg", "总进球数"), ("hafu", "半全场胜平负")]


def match_card(rec: dict) -> str:
    """单场卡片：赔率 + 去水概率 + 六玩法表。"""
    def line(play: str, labels: Dict[str, str]) -> str:
        p = rec.get("p_" + play) or {}
        o = rec.get("o_" + play) or {}
        if not o:
            return ""
        cells = "".join(
            f'<span class="pill">{_e(labels[x])} <b>{o[x]:.2f}</b> '
            f'<span class="dim">{_pct(p.get(x, 0))}</span></span>'
            for x in labels if x in o)
        return cells

    ttg = (rec.get("p_ttg") or {})
    ttg_pills = "".join(
        f'<span class="pill">{C.TTG_TOTAL_LABEL[i]} <b>{rec["o_ttg"][str(i)]:.2f}</b> '
        f'<span class="dim">{_pct(ttg.get(str(i), 0))}</span></span>'
        for i in range(8) if str(i) in (rec.get("o_ttg") or {}))

    gl = rec.get("gl")
    hhad_lab = {"h": f"让{gl}胜", "d": f"让{gl}平", "a": f"让{gl}负"}

    return f"""<div class="card">
  <div><b>{_e(rec['key'])} {_e(rec['home'])} vs {_e(rec['away'])}</b>
    <span class="dim"> · {_e(rec['league'])} · {_e(str(rec.get('date'))[5:])} {_e(str(rec.get('time'))[:5])}
    · 单关={'是' if rec.get('betting_single') in (1, '1') else '否'}</span></div>
  <table>
    <tr><th>玩法</th><th>赔率 / 市场隐含概率</th><th class="num">返还率</th></tr>
    <tr><td>胜平负</td><td>{line('had', C.HAD_LABEL)}</td><td class="num">{_pct(rec.get('r_had', 0))}</td></tr>
    <tr><td>让球胜平负</td><td>{line('hhad', hhad_lab)}</td><td class="num">{_pct(rec.get('r_hhad', 0))}</td></tr>
    <tr><td>总进球数</td><td>{ttg_pills}</td><td class="num">{_pct(rec.get('r_ttg', 0))}</td></tr>
    <tr><td>半全场</td><td>{line('hafu', C.HAFU_LABEL)}</td><td class="num">{_pct(rec.get('r_hafu', 0))}</td></tr>
  </table>
</div>"""


def report_html(matches: Dict[str, dict], title: str = "竞彩足球 · 赛事分析报告",
                read_at: Optional[str] = None, leagues: Optional[set] = None) -> str:
    read_at = read_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    sel = [r for r in matches.values()
           if (not leagues or (r.get("league") or "").strip() in leagues)]

    # 进球标尺：按联赛统计 ttg 隐含 λ（用 0–6 + 7+ 期望）
    lb: Dict[str, List[float]] = {}
    for r in sel:
        lam = sum(i * p for i, p in
                  ((int(k), v) for k, v in (r.get("p_ttg") or {}).items()))
        lam += 7 * (r.get("p_ttg") or {}).get("7", 0)
        lb.setdefault((r.get("league") or "").strip(), []).append(lam)

    rows = "".join(
        f'<tr><td>{_e(k)}</td><td class="num">{len(v)}</td>'
        f'<td class="num">{sum(v) / len(v):.2f}</td></tr>'
        for k, v in sorted(lb.items()) if v)

    body = [f"<h1>{_e(title)}</h1>",
            f'<p class="sub">生成 {read_at} ｜ 赔率读取 {read_at} ｜ 共 {len(sel)} 场</p>',
            '<div class="note"><b>⚠ 数据说明</b><br>'
            '① 赔率为中国体育彩票竞彩官方 SP，含水位；表中"隐含概率"已去水，'
            '可直接作为市场定价下的概率口径。<br>'
            '② 返还率为单腿理论值（1/Σ(1/赔率)），串关会按成分累乘下降。<br>'
            '③ 结论随时间变动，临场首发/伤停/降赔均可能推翻判断。</div>',
            '<h2>进球标尺（本报告统一校准口径）</h2>',
            '<table><tr><th>联赛</th><th class="num">样本场次</th>'
            '<th class="num">场均总进球（市场隐含 λ）</th></tr>' + rows + '</table>',
            '<h2>分场速览</h2>']
    for r in sorted(sel, key=lambda x: (str(x.get("date")), str(x.get("time") or ""))):
        body.append(match_card(r))

    body.append("""<h2>综合结论（待分析师填写）</h2>
<div class="card"><p class="dim">按 4.2 双队对比框架 × 六维定强弱差档后填入梯队表：
第一梯队（主推）/ 第二梯队（备选）/ 建议规避。</p>
<table><tr><th>梯队</th><th>场次</th><th>方向</th><th>置信度</th><th>定位</th></tr>
<tr><td>第一梯队</td><td>—</td><td>—</td><td>—/10</td><td>—</td></tr></table></div>

<h2>风险提示</h2>
<div class="card"><ul>
<li>低赔不代表低风险：赔率只反映市场定价，不改变单场的方差。</li>
<li>让球盘为整数盘（无走盘）：「让球 +1 胜」= 主队实际不输球，热门方净胜 ≥2 球即失手。</li>
<li>总进球档位是历史最高频失手点：宁可宽一档，强攻/强弱分明场上限至少 5–6 球。</li>
<li>串关容错为零：任一注要中必须两场同时命中。</li>
</ul></div>""")

    body.append("""<h2>【合规声明】</h2>
<div class="card"><ul>
<li>本报告为体育赛事数据分析，<b>不构成投注建议</b>，不承诺任何收益。</li>
<li>未满 18 周岁禁止购买彩票；请理性购彩，量力而行。</li>
<li>赔率以购票时官方为准，数据读取时间见页脚。</li>
</ul></div>""")

    foot = f"生成 {read_at} ｜ 赔率读取 {read_at} ｜ 数据来源：中国体育彩票竞彩官方接口"
    return _page(title, "\n".join(body), foot)


# ================================================================ 复盘

def review_html(ledger_summary: dict, review: Optional[str] = None,
                title: str = "竞彩足球 · 复盘报告") -> str:
    s = ledger_summary
    rows = "".join(
        f'<tr><td>{_e(r["date"])}</td><td class="num">{r["n"]}</td>'
        f'<td class="num {"ok" if r["net"] >= 0 else "bad"}">{r["net"]:+.2f}</td>'
        f'<td class="num">{r["cum"]:+.2f}</td></tr>' for r in s["curve"])

    # 累计盈亏 SVG（红涨绿跌 · 中式配色）
    svg = _curve_svg(s["curve"])

    body = [f"<h1>{_e(title)}</h1>",
            f'<p class="sub">生成 {datetime.now():%Y-%m-%d %H:%M}</p>',
            f"""<div class="kpi">
<div class="k"><div class="v">{s['tickets']}</div><div class="l">票数（已结算 {s['settled']}）</div></div>
<div class="k"><div class="v">¥{s['cost']:.0f}</div><div class="l">投入</div></div>
<div class="k"><div class="v">¥{s['payout']:.2f}</div><div class="l">回款</div></div>
<div class="k"><div class="v {'ok' if s['net'] >= 0 else 'bad'}">{s['net']:+.2f}</div><div class="l">净盈亏</div></div>
<div class="k"><div class="v">{_pct(s['return_rate'])}</div><div class="l">返还率</div></div>
</div>""",
            '<h2>累计盈亏走势</h2>', svg,
            '<h2>逐日明细</h2>',
            '<table><tr><th>日期</th><th class="num">票数</th>'
            '<th class="num">当日净</th><th class="num">累计净</th></tr>' + rows + '</table>']

    if review:
        body.append(f'<h2>复盘要点</h2><div class="card">{review}</div>')

    body.append("""<h2>【合规声明】</h2><div class="card"><ul>
<li>复盘仅用于个人决策校准，不构成投注建议。</li>
<li>理性购彩，未满 18 周岁禁止购彩。</li></ul></div>""")

    foot = f"生成 {datetime.now():%Y-%m-%d %H:%M} ｜ 数据来源：本工具包账本 data/ledger.json"
    return _page(title, "\n".join(body), foot)


def _curve_svg(curve: List[dict], w: int = 920, h: int = 260) -> str:
    """累计盈亏折线（红=盈利段 绿=亏损段，符合国内习惯）。"""
    if not curve:
        return '<div class="card dim">（暂无已结算数据）</div>'
    pad_l, pad_r, pad_t, pad_b = 56, 20, 18, 34
    vals = [0.0] + [c["cum"] for c in curve]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        hi, lo = hi + 1, lo - 1
    span = hi - lo
    n = max(1, len(curve) - 1)

    def X(i: int) -> float:
        return pad_l + i * (w - pad_l - pad_r) / n

    def Y(v: float) -> float:
        return pad_t + (hi - v) / span * (h - pad_t - pad_b)

    pts = [(X(0), Y(0.0))] + [(X(i + 1), Y(c["cum"])) for i, c in enumerate(curve)]
    zero = Y(0.0)
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    labels = "".join(
        f'<text x="{X(i + 1):.0f}" y="{h - 12}" fill="#6b7280" font-size="11" '
        f'text-anchor="middle">{_e(c["date"][5:])}</text>' for i, c in enumerate(curve))

    marks = ""
    for x, y in pts[1:]:
        col = "#c8442b" if y <= zero else "#0b6b3a"
        marks += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{col}"/>'

    return f"""<div class="card"><svg viewBox="0 0 {w} {h}" width="100%" role="img"
 aria-label="累计盈亏走势折线图"><line x1="{pad_l}" y1="{zero:.1f}" x2="{w - pad_r}" y2="{zero:.1f}"
 stroke="#c8442b" stroke-dasharray="4 4" stroke-width="1"/>
<polyline points="{poly}" fill="none" stroke="#2b6cb0" stroke-width="2.2"/>{marks}{labels}
<text x="8" y="{Y(hi) + 4:.0f}" fill="#6b7280" font-size="11">{hi:+.0f}</text>
<text x="8" y="{Y(lo):.0f}" fill="#6b7280" font-size="11">{lo:+.0f}</text></svg></div>"""
