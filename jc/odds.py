# -*- coding: utf-8 -*-
"""赔率解析与去水（隐含概率）。

竞彩赔率是"含水位"的：三档隐含概率之和 > 1，多余的部分就是机构的返还率缺口。
去水后得到"市场隐含概率"——本包所有组合测算（中奖/全中/盈利概率）都建立在这个
概率口径上，而不是简单用赔率倒数。
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from . import config as C


def devig(d: Dict[str, object]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """输入 {选项: 赔率}，返回 (去水概率, 原始赔率)。

    只保留能转成 float 且 > 1 的项；全空则返回 ({}, {})。
    """
    inv: Dict[str, float] = {}
    odds: Dict[str, float] = {}
    for k, v in (d or {}).items():
        try:
            f = float(v)          # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if f > 1:
            inv[k] = 1.0 / f
            odds[k] = f
    if not inv:
        return {}, {}
    s = sum(inv.values())
    return {k: v / s for k, v in inv.items()}, odds


def payout_rate(d: Dict[str, object]) -> float:
    """返还率 = 1 / Σ(1/赔率)。竞彩单腿实测：had/hhad ≈ 88.6%，ttg/hafu ≈ 79.8%。"""
    _, odds = devig(d)
    if not odds:
        return 0.0
    return 1.0 / sum(1.0 / o for o in odds.values())


def subs(pool_resp: dict) -> list:
    """把接口返回的嵌套结构摊平成场次列表。"""
    out = []
    for m in (pool_resp or {}).get("value", {}).get("matchInfoList", []) or []:
        out.extend(m.get("subMatchList", []) or [])
    return out


def build_index(pools: Dict[str, dict]) -> Dict[str, Dict[str, dict]]:
    """各池**独立**建索引（严禁跨池 update 合并）。

    返回 {pool: {matchNumStr: 场次原始对象}}。
    """
    return {p: {s.get("matchNumStr"): s for s in subs(resp)}
            for p, resp in (pools or {}).items()}


def base_index(pools: Dict[str, dict]) -> Dict[str, dict]:
    """基准场次索引：取覆盖最全的池（实测 ttg），缺则退回场次最多的池。"""
    idx = build_index(pools)
    if C.BASE_POOL in idx and idx[C.BASE_POOL]:
        return idx[C.BASE_POOL]
    if not idx:
        return {}
    best = max(idx.values(), key=len)
    return best


def merge_match(k: str, idx: Dict[str, Dict[str, dict]]) -> dict:
    """按 matchNumStr 把各池的玩法对象**逐字段取非空值**合并到一条记录。

    遵守两条禁忌：不整块 update；基准元数据取自基准池。
    """
    rec: dict = {"key": k}

    for pool in C.POOLS:
        s = (idx.get(pool) or {}).get(k) or {}
        # 元数据优先取第一个有值的池
        if not rec.get("home") and s.get("homeTeamAbbName"):
            for src, dst in (
                ("homeTeamAbbName", "home"), ("awayTeamAbbName", "away"),
                ("leagueAbbName", "league"), ("matchDate", "date"),
                ("matchTime", "time"), ("matchStatus", "status"),
                ("bettingSingle", "betting_single"), ("bettingAllUp", "betting_allup"),
                ("homeRank", "home_rank"), ("awayRank", "away_rank"),
            ):
                rec[dst] = s.get(src)
        # 玩法对象：只在本池返回非空时写入
        obj = s.get(pool)
        if isinstance(obj, dict) and obj:
            rec[pool] = obj

    return rec


def enrich(rec: dict) -> dict:
    """给一条场次记录补齐去水概率与赔率字典，供下游测算直接调用。"""
    had = rec.get("had") or {}
    hhad = rec.get("hhad") or {}
    ttg = rec.get("ttg") or {}
    hafu = rec.get("hafu") or {}
    crs = rec.get("crs") or {}

    rec["gl"] = hhad.get("goalLine")           # 让球数
    rec["p_had"], rec["o_had"] = devig({x: had.get(x) for x in ("h", "d", "a")})
    rec["p_hhad"], rec["o_hhad"] = devig({x: hhad.get(x) for x in ("h", "d", "a")})
    rec["p_ttg"], rec["o_ttg"] = devig({str(i): ttg.get(f"s{i}") for i in range(8)})
    rec["p_hafu"], rec["o_hafu"] = devig({x: hafu.get(x) for x in C.HAFU_LABEL})
    rec["p_crs"], rec["o_crs"] = devig(crs)

    rec["r_had"] = payout_rate({x: had.get(x) for x in ("h", "d", "a")})
    rec["r_hhad"] = payout_rate({x: hhad.get(x) for x in ("h", "d", "a")})
    rec["r_ttg"] = payout_rate({str(i): ttg.get(f"s{i}") for i in range(8)})
    rec["r_hafu"] = payout_rate({x: hafu.get(x) for x in C.HAFU_LABEL})

    rec["vs"] = f"{rec.get('home')} vs {rec.get('away')}"
    return rec


def settle(matches: Iterable[dict]) -> Dict[str, dict]:
    """对一批场次批量 enrich，返回 {matchNumStr: 记录}。"""
    return {m["key"]: enrich(m) for m in matches}
