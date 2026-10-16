# -*- coding: utf-8 -*-
"""战绩账本：把每张实购票落库，让复盘和校准自动化。

一条记录 = 一张实购票。字段设计成"能否算清净收益"为第一优先：
买什么、花多少、回多少、什么时候、什么结构、当时怎么判断的。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional

from . import config as C


def _load() -> dict:
    if not C.LEDGER.exists():
        return {"tickets": []}
    try:
        return json.loads(C.LEDGER.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tickets": []}


def _save(d: dict) -> None:
    C.LEDGER.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- 增改

def add(record: dict) -> dict:
    """登记一张票。record 至少含 date / legs / cost；其余字段可选。"""
    d = _load()
    rec = dict(
        id=record.get("id") or f"{record.get('date', '?')}-{len(d['tickets']) + 1:02d}",
        date=record.get("date"),
        play=record.get("play", ""),            # 玩法构成，如 "总进球+胜平负"
        structure=record.get("structure", ""),  # 过关方式，如 "3串3"
        legs=record.get("legs", []),            # [{key,name,odd,prob}]
        bets=record.get("bets"),
        multiple=record.get("multiple", 1),
        cost=float(record.get("cost", 0)),
        payout=float(record.get("payout", 0)),  # 0 = 未结算
        settled=bool(record.get("settled", False)),
        note=record.get("note", ""),
    )
    d["tickets"].append(rec)
    _save(d)
    return rec


def settle(ticket_id: str, payout: float, results: Optional[dict] = None) -> dict:
    """结算一张票：填回款与各腿赛果。"""
    d = _load()
    for t in d["tickets"]:
        if t["id"] == ticket_id:
            t["payout"] = float(payout)
            t["settled"] = True
            if results:
                t["results"] = results
            _save(d)
            return t
    raise KeyError(f"找不到票 {ticket_id}")


def get(ticket_id: str) -> Optional[dict]:
    for t in _load()["tickets"]:
        if t["id"] == ticket_id:
            return t
    return None


def all_tickets() -> List[dict]:
    return _load()["tickets"]


# ---------------------------------------------------------------- 统计

def summary() -> dict:
    """累计盈亏 + 按日期/玩法/结构的分解。"""
    ts = _load()["tickets"]
    settled = [t for t in ts if t.get("settled")]
    cost = sum(t["cost"] for t in ts)
    payout = sum(t["payout"] for t in ts)
    net = payout - cost

    by_date: Dict[str, dict] = {}
    for t in ts:
        d = by_date.setdefault(t["date"], {"cost": 0.0, "payout": 0.0, "n": 0})
        d["cost"] += t["cost"]
        d["payout"] += t["payout"]
        d["n"] += 1

    # 累计净（按日期升序）
    cum, curve = 0.0, []
    for day in sorted(by_date):
        cum += by_date[day]["payout"] - by_date[day]["cost"]
        curve.append({"date": day, "net": by_date[day]["payout"] - by_date[day]["cost"],
                      "cum": cum, "n": by_date[day]["n"]})

    return dict(
        tickets=len(ts), settled=len(settled),
        cost=cost, payout=payout, net=net,
        return_rate=(payout / cost if cost else 0.0),
        win_rate=(len([t for t in settled if t["payout"] > t["cost"]]) / len(settled)
                  if settled else 0.0),
        by_date=by_date, curve=curve,
    )


def render_text() -> str:
    s = summary()
    lines = [f"竞彩战绩账本 · {s['tickets']} 张票（已结算 {s['settled']}）",
             f"投入 {s['cost']:.0f} / 回款 {s['payout']:.2f} / 净 {s['net']:+.2f} / "
             f"返还率 {s['return_rate'] * 100:.1f}%", "-" * 56]
    for row in s["curve"]:
        lines.append(f"  {row['date']}  {row['n']}张  当日 {row['net']:+8.2f}  "
                     f"累计 {row['cum']:+8.2f}")
    return "\n".join(lines)
