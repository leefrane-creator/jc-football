# -*- coding: utf-8 -*-
"""腿池：把一场场比赛摊平成"可下注的最小单位"（腿）。

一条腿 = 一个场次的一种玩法的一个选项（含让球数、赔率、去水概率）。
后续所有组合、测算、出票都在腿池上做。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from . import config as C
from . import fetch as F
from . import odds as O


# ---------------------------------------------------------------- 构造

def match_legs(rec: dict) -> List[dict]:
    """把一条 enriched 场次记录展开成全部候选腿。"""
    legs: List[dict] = []
    k = rec["key"]
    common = dict(k=k, league=rec.get("league"), home=rec.get("home"),
                  away=rec.get("away"), vs=rec.get("vs"),
                  date=rec.get("date"), time=rec.get("time"),
                  single=rec.get("betting_single"))

    # 胜平负
    for x in ("h", "d", "a"):
        o = (rec.get("o_had") or {}).get(x)
        if not o:
            continue
        legs.append(dict(common, play="had", pick=x,
                         name=f"胜平负·{C.HAD_LABEL[x]}", odd=o,
                         prob=(rec.get("p_had") or {}).get(x, 0.0), line=None))

    # 让球胜平负
    gl = rec.get("gl")
    for x in ("h", "d", "a"):
        o = (rec.get("o_hhad") or {}).get(x)
        if not o:
            continue
        legs.append(dict(common, play="hhad", pick=x,
                         name=f"让{gl}·{C.HHAD_SHORT[x]}", odd=o,
                         prob=(rec.get("p_hhad") or {}).get(x, 0.0), line=gl))

    # 半全场
    for x, lab in C.HAFU_LABEL.items():
        o = (rec.get("o_hafu") or {}).get(x)
        if not o:
            continue
        legs.append(dict(common, play="hafu", pick=x, name=f"半全场·{lab}",
                         odd=o, prob=(rec.get("p_hafu") or {}).get(x, 0.0), line=None))

    # 总进球（0..7+ 共 8 档）
    for i in range(8):
        o = (rec.get("o_ttg") or {}).get(str(i))
        if not o:
            continue
        legs.append(dict(common, play="ttg", pick=str(i),
                         name=f"总进球·{C.TTG_TOTAL_LABEL[i]}", odd=o,
                         prob=(rec.get("p_ttg") or {}).get(str(i), 0.0), line=None))

    return legs


def build_legs(matches: Dict[str, dict],
               leagues: Optional[set] = None,
               status: str = "Selling") -> List[dict]:
    """从 {场次: enriched 记录} 构建腿池，可按联赛与销售状态过滤。"""
    out: List[dict] = []
    for rec in matches.values():
        if leagues and (rec.get("league") or "").strip() not in leagues:
            continue
        if status and rec.get("status") != status:
            continue
        out.extend(match_legs(rec))
    return out


# ---------------------------------------------------------------- 落盘

def legs_path(date: str) -> Path:
    return C.DATA / "legs" / f"{date}.json"


def save_legs(legs: List[dict], date: str) -> Path:
    legs_path(date).parent.mkdir(parents=True, exist_ok=True)
    p = legs_path(date)
    p.write_text(json.dumps(legs, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def load_legs(date: str) -> Optional[List[dict]]:
    p = legs_path(date)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 便捷

def from_snapshot(date: str, leagues: Optional[set] = None) -> List[dict]:
    """从某日快照直接建腿池（不联网）。"""
    pools = F.load_snapshot(date)
    if not pools:
        raise FileNotFoundError(f"没有 {date} 的快照，请先 jc fetch {date}")
    idx = O.build_index(pools)
    base = O.base_index(pools)
    matches = {k: O.enrich(O.merge_match(k, idx)) for k in base}
    return build_legs(matches, leagues=leagues)


def index_matches(date: str) -> Dict[str, dict]:
    """返回 {场次: enriched 记录}（用于出票单/报告）。"""
    pools = F.load_snapshot(date) or {}
    idx = O.build_index(pools)
    base = O.base_index(pools)
    return {k: O.enrich(O.merge_match(k, idx)) for k in base}
