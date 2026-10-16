# -*- coding: utf-8 -*-
"""把 2026-10-09 ~ 10-16 的 9 张实购票录入账本（一次性脚本）。

数据来源：项目工作日志 2026-10-09.md ~ 2026-10-16.md 的账本表。
合计：投入 620 / 回款 537.26 / 净 −82.74。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jc import ledger as LD  # noqa: E402

TICKETS = [
    # date, play, structure, cost, payout, note
    ("2026-10-10", "总进球", "3串1", 162, 0.0,
     "英超西甲 4 场宽覆盖 · 81 注 · 全灭（3串1 错 2 场必全灭）"),
    ("2026-10-11", "胜平负+总进球", "2串1", 32, 0.0,
     "2 场 8 组合 · 全灭"),
    ("2026-10-12", "胜平负+总进球", "3串4", 54, 42.44,
     "3 场 3串4 · 错 1 场中 1 注 2串1"),
    ("2026-10-12", "胜平负+总进球", "2串1", 20, 0.0,
     "2 场 2串1 · 全灭（共用 007/008 场次，与上票双杀）"),
    ("2026-10-13", "总进球", "3串4·8倍", 64, 0.0,
     "欧冠 3 场 · 方向全对但被「胜/胜」抬赔双挂"),
    ("2026-10-14", "总进球", "3串3", 96, 147.0,
     "用户票① 48 注纯 2串1 · 011 曼城上沿留到 6 球 → 中奖，净 +51"),
    ("2026-10-14", "总进球", "2串1", 48, 121.67,
     "用户票② · 净 +73.67"),
    ("2026-10-15", "让球+总进球", "3串3", 96, 180.15,
     "票① 3串3 · 净 +84.15"),
    ("2026-10-15", "胜平负", "2串1", 48, 46.0,
     "票② 2串1 · 净 −2（稳胆票被改成博冷票，少赚 116）"),
]


def main() -> None:
    # 清空重建，保证幂等
    if LD.C.LEDGER.exists():
        LD.C.LEDGER.unlink()
    for date, play, structure, cost, payout, note in TICKETS:
        LD.add(dict(date=date, play=play, structure=structure,
                    cost=cost, payout=payout, settled=True, note=note))
    print(LD.render_text())


if __name__ == "__main__":
    main()
