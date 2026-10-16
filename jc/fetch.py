# -*- coding: utf-8 -*-
"""取数：抓取 5 个玩法池，并**强制落盘快照**。

为什么必须落盘：体彩网对已过期场次**不再返回赔率**。不存快照，第二天就
无法复盘票面赔率。所以 `fetch()` 抓完一定写 `data/odds/YYYY-MM-DD.json`。
"""
from __future__ import annotations

import json
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from . import config as C
from . import odds as O

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def fetch_pool(pool: str, timeout: int = 40) -> dict:
    """抓单个玩法池的原始 JSON。"""
    url = f"{C.API}?poolCode={pool}&channel=c&pageSize=100&pageNo=1"
    req = urllib.request.Request(url, headers=C.HEADERS)
    raw = urllib.request.urlopen(req, context=_CTX, timeout=timeout).read()
    return json.loads(raw.decode("utf-8"))


def fetch_all(pools: Optional[list] = None, timeout: int = 40) -> Dict[str, dict]:
    """抓全部玩法池。单池失败不中断，返回成功的部分并告警。"""
    pools = pools or list(C.POOLS)
    out: Dict[str, dict] = {}
    for p in pools:
        try:
            out[p] = fetch_pool(p, timeout=timeout)
            n = len(O.subs(out[p]))
            print(f"  {p:<5} {n:>3} 场  ok")
        except Exception as e:                     # noqa: BLE001
            print(f"  {p:<5} FAIL  {type(e).__name__}: {e}")
            out[p] = {}
    return out


def snapshot_path(date: Optional[str] = None) -> Path:
    date = date or datetime.now().strftime("%Y-%m-%d")
    return C.ODDS_DIR / f"{date}.json"


def save_snapshot(pools: Dict[str, dict], date: Optional[str] = None) -> Path:
    """把原始池数据 + 读取时间戳落盘。"""
    p = snapshot_path(date)
    payload = {
        "read_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "read_date": date or datetime.now().strftime("%Y-%m-%d"),
        "pools": pools,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def load_snapshot(date: str) -> Optional[dict]:
    """读取某日快照，返回原始池数据（不含时间戳字段）。"""
    p = snapshot_path(date)
    if not p.exists():
        return None
    payload = json.loads(p.read_text(encoding="utf-8"))
    return payload.get("pools", {})


def list_snapshots() -> list:
    return sorted(p.stem for p in C.ODDS_DIR.glob("*.json"))


def fetch_snapshot(date: Optional[str] = None, save: bool = True,
                   pools: Optional[list] = None) -> Dict[str, dict]:
    """抓取 + （默认）落盘。返回原始池数据。"""
    pools = pools or list(C.POOLS)
    data = fetch_all(pools)
    if save and any(data.values()):
        p = save_snapshot(data, date)
        print(f"  ↳ 快照已落盘 {p}")
    return data


def load_or_fetch(date: Optional[str] = None, pools: Optional[list] = None) -> Dict[str, dict]:
    """优先读快照（赛前已存则直接用，保证口径一致），没有则现抓。"""
    if date:
        snap = load_snapshot(date)
        if snap:
            print(f"  ↳ 命中快照 {snapshot_path(date)}")
            return snap
    return fetch_snapshot(date, save=True, pools=pools)
