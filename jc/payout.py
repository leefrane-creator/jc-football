# -*- coding: utf-8 -*-
"""单票回款分布：分情形概率与金额、最可能的全中组合。

用于"这张票值不值"的测算，字段刻意对齐专家包的铁律 19/20/21：
中奖概率、盈利概率、错 1 腿回款/成本、全中回款区间、假中奖缺口。
"""
from __future__ import annotations

import itertools
from typing import List, Sequence

from . import config as C
from . import scheme as S


def scenario_table(legs: Sequence[dict], unit: float = C.UNIT) -> dict:
    """按"命中几条腿"分组，给出概率、回款区间、回本率。"""
    legs = [S.as_leg(L) for L in legs]
    N = len(legs)
    m = S.metrics(legs, unit=unit)

    rows = []
    for hits in range(N, 0, -1):
        pr = m["prob_by_hits"].get(hits, 0.0)
        if pr <= 1e-12:
            continue
        lo, hi = m["pay_by_hits"].get(hits, (0.0, 0.0))
        label = {N: "全中", N - 1: "错 1 腿", N - 2: "错 2 腿", N - 3: "错 3 腿"}.get(
            hits, f"中 {hits} 腿")
        rows.append(dict(hits=hits, label=label, prob=pr, pay_min=lo, pay_max=hi,
                         recover_min=lo / m["cost"] if m["cost"] else 0,
                         recover_max=hi / m["cost"] if m["cost"] else 0))

    return dict(metrics=m, rows=rows,
                fake_gap=max(0.0, m["win"] - m["prof"]),
                note=(
                    "中奖概率 - 盈利概率 = 假中奖缺口：这些结果是'中了但没回本'。"
                    if m["win"] - m["prof"] > 0.02 else
                    "中奖概率 = 盈利概率，票面无假中奖（干净结构）。"
                ))


def top_full_combos(legs: Sequence[dict], unit: float = C.UNIT, top: int = 10) -> List[dict]:
    """最可能出现的全中组合（每腿取其概率最高的档），按概率降序。"""
    legs = [S.as_leg(L) for L in legs]
    N = len(legs)
    combos = []
    choices = [list(range(len(L["odds"]))) for L in legs]
    for combo in itertools.product(*choices):
        pr = 1.0
        pay = 0.0
        for i, c in enumerate(combo):
            pr *= legs[i]["probs"][c]
        for i, j in itertools.combinations(range(N), 2):
            pay += unit * legs[i]["odds"][combo[i]] * legs[j]["odds"][combo[j]]
        combos.append(dict(picks=list(combo), prob=pr, payout=pay,
                           labels=[legs[i]["name"] for i in range(N)],
                           odds=[legs[i]["odds"][combo[i]] for i in range(N)]))
    combos.sort(key=lambda x: -x["prob"])
    return combos[:top]


def render_text(legs: Sequence[dict], unit: float = C.UNIT, title: str = "票面测算") -> str:
    legs = [S.as_leg(L) for L in legs]
    r = scenario_table(legs, unit)
    m = r["metrics"]
    out = [f"===== {title} =====",
           f"{m['N']} 腿 · {m['bets']} 注 · {m['cost']:.0f} 元 · 过关方式 = 纯 2串1",
           ""]
    for L in legs:
        bands = "/".join(f"{o:.2f}({p * 100:.0f}%)" for o, p in zip(L["odds"], L["probs"]))
        out.append(f"  {L['key']} {L['name']:<14} @{bands}")
    out += ["", f"{'情形':<10}{'概率':>9}{'回款区间':>20}{'回本率':>16}"]
    for row in r["rows"]:
        out.append(f"  {row['label']:<10}{row['prob'] * 100:>8.2f}%"
                   f"{row['pay_min']:>10.2f}–{row['pay_max']:<8.2f}"
                   f"{row['recover_min'] * 100:>7.0f}%–{row['recover_max'] * 100:<6.0f}%")
    out += ["",
            f"中奖概率 {m['win'] * 100:.2f}%   盈利概率 {m['prof'] * 100:.2f}%   "
            f"全中概率 {m['full'] * 100:.2f}%",
            f"错 1 腿最差回款/成本 = {m['fault_recover'] * 100:.0f}%   "
            f"（{'可回本' if m['fault_recover'] >= 1 else '不能回本'}）",
            f"期望回款 {m['exp_payout']:.2f} 元  净期望 {m['exp_net']:+.2f} 元   "
            f"返还率 {m['return_rate'] * 100:.1f}%",
            f"→ {r['note']}"]
    return "\n".join(out)
