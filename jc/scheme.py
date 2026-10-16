# -*- coding: utf-8 -*-
"""组合测算与方案搜索。

核心口径（务必分清）：
  · 中奖概率 = P(回款 > 0)      —— 至少中一注
  · 全中概率 = P(所有腿都命中)   —— N串1 才中的口径
  · 盈利概率 = P(回款 > 成本)    —— 真正"赚钱"的概率
竞彩很容易出现"中了却亏"的假中奖，三个数必须分开报。
"""
from __future__ import annotations

import itertools
from typing import Dict, Iterable, List, Optional, Sequence

from . import config as C


# ---------------------------------------------------------------- 腿的规整

def as_leg(leg: dict) -> dict:
    """把一条腿规整成 {key, name, odds:[...], probs:[...]} 的复式形式。"""
    if "odds" in leg and isinstance(leg["odds"], (list, tuple)):
        odds = [float(x) for x in leg["odds"]]
        probs = [float(x) for x in leg.get("probs", [])] or [0.0] * len(odds)
    else:
        odds = [float(leg["odd"])]
        probs = [float(leg.get("prob", 0.0))]
    return dict(key=leg.get("k") or leg.get("key"), name=leg.get("name", ""),
                league=leg.get("league"), home=leg.get("home"), away=leg.get("away"),
                vs=leg.get("vs") or (f"{leg.get('home')} vs {leg.get('away')}"
                                     if leg.get("home") else ""),
                date=leg.get("date"), time=leg.get("time"), play=leg.get("play"),
                line=leg.get("line"), pick=leg.get("pick"),
                odds=odds, probs=probs)


def bets_of(legs: Sequence[dict]) -> int:
    """复式纯 2串1 的注数 = 各腿两两的档数之积之和。"""
    n = [len(L["odds"]) for L in legs]
    return sum(n[i] * n[j] for i, j in itertools.combinations(range(len(n)), 2))


# ---------------------------------------------------------------- 测算

def metrics(legs: Sequence[dict], unit: float = C.UNIT, mode: str = "2x1") -> dict:
    """穷举所有结果，精确算分情形概率与回款。

    mode: '2x1' 纯 2串1（默认）；'3x1' 时额外含 N串1 成分（用于对照）。
    """
    legs = [as_leg(L) for L in legs]
    N = len(legs)
    n_bands = [len(L["odds"]) for L in legs]

    # 纯 2串1 成分注数 = 各腿两两档数之积之和
    bets = sum(n_bands[i] * n_bands[j] for i, j in itertools.combinations(range(N), 2))
    if mode != "2x1":
        # 追加 N串1 成分：注数 = Π 各腿档数（对照用，水钱会被累乘吃掉）
        prod = 1
        for n in n_bands:
            prod *= n
        bets += prod
    cost = unit * bets

    # 每条腿的命中概率
    p_hit = [sum(L["probs"]) for L in legs]

    win = prof = full_pr = 0.0
    exp = 0.0
    by_hits: Dict[int, List[float]] = {}

    def payout(chosen: List[int]) -> float:
        """chosen[i] = 命中的档位下标，-1 表示该腿失手。"""
        pay = 0.0
        for i, j in itertools.combinations(range(N), 2):
            if chosen[i] >= 0 and chosen[j] >= 0:
                pay += unit * legs[i]["odds"][chosen[i]] * legs[j]["odds"][chosen[j]]
        if mode != "2x1":
            allhit = all(c >= 0 for c in chosen)
            if allhit:
                prod = unit
                for i, c in enumerate(chosen):
                    prod *= legs[i]["odds"][c]
                pay += prod
        return pay

    # 枚举：每条腿 = [某个档位下标] 或 [-1]
    choices = [list(range(len(L["odds"]))) + [-1] for L in legs]
    for combo in itertools.product(*choices):
        pr = 1.0
        for i, c in enumerate(combo):
            if c < 0:
                pr *= max(0.0, 1.0 - p_hit[i])
            else:
                pr *= legs[i]["probs"][c]
        if pr <= 0:
            continue
        pay = payout(list(combo))
        exp += pr * pay
        if pay > 0:
            win += pr
        if pay > cost:
            prof += pr
        hits = sum(1 for c in combo if c >= 0)
        by_hits.setdefault(hits, []).append(pay)
        if hits == N:
            full_pr += pr

    def rng(hits: int):
        v = by_hits.get(hits)
        return (min(v), max(v)) if v else (0.0, 0.0)

    def prob(hits: int) -> float:
        """恰好命中 hits 条腿的概率。"""
        tot = 0.0
        for combo in itertools.product(*choices):
            if sum(1 for c in combo if c >= 0) != hits:
                continue
            pr = 1.0
            for i, c in enumerate(combo):
                pr *= legs[i]["probs"][c] if c >= 0 else max(0.0, 1.0 - p_hit[i])
            tot += pr
        return tot

    res = dict(
        N=N, bets=bets, cost=cost, unit=unit, mode=mode,
        win=win, prof=prof, full=full_pr,
        p_hit=p_hit, full_pay=rng(N),
        pay_by_hits={h: rng(h) for h in range(N, 0, -1)},
        prob_by_hits={h: prob(h) for h in range(N, 0, -1)},
        exp_payout=exp, exp_net=exp - cost,
        return_rate=(exp / cost if cost else 0.0),
    )
    # 容错：最差的一次"错 1 腿"回款
    res["worst1"] = rng(N - 1)[0] if N >= 2 else 0.0
    res["fault_recover"] = (res["worst1"] / cost) if cost else 0.0
    return res


def fault_tolerant(legs: Sequence[dict], unit: float = C.UNIT) -> bool:
    """严格判据：错 1 腿（最差的那一对）也能回本。

    对 3 腿单档 `3串3`：等价于 三腿两两赔率积的最小值 ≥ 3。
    """
    m = metrics(legs, unit=unit)
    return m["worst1"] >= m["cost"]


# ---------------------------------------------------------------- 搜索

def search(pool: Sequence[dict], n_legs: int, top: int = 10,
           rank: str = "prof", require_fault: bool = True,
           odds_range: Optional[tuple] = None,
           distinct_match: bool = True) -> List[dict]:
    """在腿池中穷举 n_legs 腿组合，按 rank('prof'|'win'|'full') 排序。"""
    cand = list(pool)
    if odds_range:
        lo, hi = odds_range
        cand = [L for L in cand if lo <= float(L["odd"]) <= hi]

    out = []
    for cb in itertools.combinations(cand, n_legs):
        if distinct_match and len({L["k"] for L in cb}) < n_legs:
            continue
        try:
            m = metrics(cb)
        except Exception:                          # noqa: BLE001
            continue
        if require_fault and m["worst1"] < m["cost"]:
            continue
        out.append((m[rank], m, cb))
    out.sort(key=lambda x: -x[0])

    # 去重（同场次集合只留最优）
    seen, res = set(), []
    for val, m, cb in out:
        sig = tuple(sorted(L["k"] for L in cb))
        if sig in seen:
            continue
        seen.add(sig)
        res.append(dict(metrics=m, legs=[as_leg(L) for L in cb]))
        if len(res) >= top:
            break
    return res


def frontier(pool: Sequence[dict], max_legs: int = 5, top: int = 1) -> Dict[int, dict]:
    """各腿数下、在'严格错 1 腿回本'约束下的最优（按盈利 / 按中奖分别取）。"""
    rows: Dict[int, dict] = {}
    for n in range(3, max_legs + 1):
        best_prof = search(pool, n, top=top, rank="prof")
        best_win = search(pool, n, top=top, rank="win")
        rows[n] = dict(best_prof=best_prof[0] if best_prof else None,
                       best_win=best_win[0] if best_win else None)
    return rows


def joint(tickets: Iterable[Sequence[dict]], unit: float = C.UNIT) -> dict:
    """多张票一起买时的联合分布（用于验证"多票稀释盈利概率"）。"""
    tickets = [[as_leg(L) for L in t] for t in tickets]
    total_cost = 0.0
    total_bets = 0
    for t in tickets:
        total_bets += bets_of(t)
        total_cost += unit * bets_of(t)

    exp = win = prof = 0.0
    for picks in itertools.product(*[
        list(itertools.product(*[(list(range(len(L["odds"]))) + [-1]) for L in t]))
        for t in tickets
    ]):
        pr = 1.0
        pay = 0.0
        for t, combo in zip(tickets, picks):
            p_hit = [sum(L["probs"]) for L in t]
            for i, c in enumerate(combo):
                pr *= t[i]["probs"][c] if c >= 0 else max(0.0, 1.0 - p_hit[i])
            for i, j in itertools.combinations(range(len(t)), 2):
                if combo[i] >= 0 and combo[j] >= 0:
                    pay += unit * t[i]["odds"][combo[i]] * t[j]["odds"][combo[j]]
        if pr <= 0:
            continue
        exp += pr * pay
        if pay > 0:
            win += pr
        if pay > total_cost:
            prof += pr

    return dict(bets=total_bets, cost=total_cost, win=win, prof=prof,
                exp_payout=exp, exp_net=exp - total_cost,
                return_rate=(exp / total_cost if total_cost else 0.0))
