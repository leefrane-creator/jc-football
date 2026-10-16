# -*- coding: utf-8 -*-
"""命令行入口：python -m jc <命令>

命令一览
  fetch     抓取赔率并落盘快照
  snapshots 列出已有快照
  legs      从快照建腿池并打印候选腿
  scheme    在腿池中搜索"错 1 腿回本 + 最优盈利/中奖"方案
  payout    测算指定组合的分情形回款
  ticket    生成出票单 HTML（仿彩票 APP 购买详情页）
  report    生成赛事分析报告 HTML
  review    从账本生成复盘报告 HTML
  ledger    账本读写（add / settle / show）
  info      显示配置与路径
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import config as C
from . import fetch as F
from . import legs as LG
from . import odds as O
from . import payout as PO
from . import render as R
from . import scheme as S
from . import ledger as LD


# ---------------------------------------------------------------- 工具

def _load_matches(date: str) -> Dict[str, dict]:
    pools = F.load_snapshot(date)
    if not pools:
        print(f"没有 {date} 的快照，先跑：python -m jc fetch --date {date}", file=sys.stderr)
        sys.exit(2)
    idx = O.build_index(pools)
    base = O.base_index(pools)
    return {k: O.enrich(O.merge_match(k, idx)) for k in base}


def _parse_legs(spec: str, matches: Dict[str, dict]) -> List[dict]:
    """解析 key:play:pick[+pick] 列表，逗号分隔。

    例：周六013:ttg:3+4+5,周六017:had:a
    """
    out = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, play, picks = chunk.split(":")
        rec = matches.get(key)
        if not rec:
            raise KeyError(f"快照里没有场次 {key}")
        p = rec.get("p_" + play) or {}
        o = rec.get("o_" + play) or {}
        odds, probs = [], []
        for pk in picks.split("+"):
            if pk not in o:
                raise KeyError(f"{key} 的 {play} 没有 {pk} 档")
            odds.append(float(o[pk]))
            probs.append(float(p.get(pk, 0.0)))
        name = _leg_name(play, picks, rec)
        out.append(dict(k=key, name=name, odds=odds, probs=probs, play=play,
                        league=rec.get("league"), home=rec.get("home"),
                        away=rec.get("away"), date=rec.get("date"),
                        time=rec.get("time"), line=rec.get("gl")))
    return out


def _leg_name(play: str, picks: str, rec: dict) -> str:
    if play == "had":
        lab = "/".join(C.HAD_LABEL[x] for x in picks.split("+"))
        return f"胜平负·{lab}"
    if play == "hhad":
        lab = "/".join(C.HHAD_SHORT[x] for x in picks.split("+"))
        return f"让{rec.get('gl')}·{lab}"
    if play == "hafu":
        lab = "/".join(C.HAFU_LABEL[x] for x in picks.split("+"))
        return f"半全场·{lab}"
    if play == "ttg":
        lab = "/".join(C.TTG_TOTAL_LABEL[int(x)] for x in picks.split("+"))
        return f"总进球·{lab}" + ("（复式）" if "+" in picks else "")
    return play


def _write_html(name: str, html_text: str) -> str:
    """name 含路径分隔符时按当前目录解析，否则落到 OUTPUTS。"""
    p = Path(name)
    if not p.is_absolute():
        p = p if (len(p.parts) > 1) else (C.OUTPUTS / p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_text, encoding="utf-8")
    print(f"  ↳ 已写出 {p}")
    return str(p)


# ---------------------------------------------------------------- 命令

def cmd_fetch(a) -> None:
    print(f"抓取 5 池（{', '.join(C.POOLS)}）…")
    F.fetch_snapshot(a.date, save=True)


def cmd_snapshots(a) -> None:
    snaps = F.list_snapshots()
    print(f"快照目录 {C.ODDS_DIR}")
    for s in snaps:
        payload = json.loads((C.ODDS_DIR / f"{s}.json").read_text(encoding="utf-8"))
        n = sum(len(O.subs(v)) for v in payload.get("pools", {}).values())
        print(f"  {s}  读取于 {payload.get('read_at')}  共 {n} 条池记录")


def cmd_legs(a) -> None:
    matches = _load_matches(a.date)
    leagues = set(a.league.split(",")) if a.league else C.MAIN_LEAGUES
    ls = LG.build_legs(matches, leagues=leagues)
    LG.save_legs(ls, a.date)
    print(f"{a.date} 五大联赛腿池：{len(ls)} 条（已存 data/legs/{a.date}.json）")
    for play, label in [("had", "胜平负"), ("hhad", "让球"), ("hafu", "半全场")]:
        sub = [L for L in ls if L["play"] == play]
        print(f"\n—— {label} · 赔率 1.60–2.40 且概率 ≥ 40% ——")
        rows = sorted([L for L in sub if 1.60 <= L["odd"] <= 2.40 and L["prob"] >= 0.40],
                      key=lambda x: -x["prob"])
        for L in rows[:20]:
            print(f"  {L['prob'] * 100:5.1f}%  @{L['odd']:5.2f}  {L['k']} {L['league']:<3} "
                  f"{L['vs']:<20} {L['name']}")


def cmd_scheme(a) -> None:
    import itertools as _it
    matches = _load_matches(a.date)
    leagues = set(a.league.split(",")) if a.league else C.MAIN_LEAGUES
    ls = LG.build_legs(matches, leagues=leagues)
    pool = [L for L in ls if L["play"] in ("had", "hhad")]
    rng = a.odds_range or "1.40-2.20"
    lo, hi = (float(x) for x in rng.split("-"))
    pool = [L for L in pool if lo <= L["odd"] <= hi]
    print(f"腿池 {len(pool)} 条（胜平负+让球，赔率 {rng}）"
          f"｜ 严格约束：错 1 腿回本 ≥ 成本")
    for n in ([a.legs] if a.legs else [3, 4, 5]):
        total = len(list(_it.combinations(range(len(pool)), n)))
        if total > 4_000_000:
            print(f"\n===== N={n} 组合数 {total:,} 过大，已跳过（请收窄 --odds-range）=====")
            continue
        res = S.search(pool, n, top=a.top, rank=a.rank)
        print(f"\n===== N={n} · 组合 {total:,} · 按 "
              f"{'盈利' if a.rank == 'prof' else ('中奖' if a.rank == 'win' else '全中')}"
              f" 概率最优 =====")
        for i, r in enumerate(res, 1):
            m = r["metrics"]
            print(f"#{i} {m['bets']}注/{m['cost']:.0f}元 | 中奖 {m['win'] * 100:.1f}% "
                  f"盈利 {m['prof'] * 100:.1f}% 全中 {m['full'] * 100:.2f}% | "
                  f"错1腿回 {m['fault_recover'] * 100:.0f}%")
            for L in r["legs"]:
                print(f"     {L['key']} {L['league']:<3} {L['vs']:<20} {L['name']:<13} "
                      f"@{L['odds'][0]:.2f} p={L['probs'][0] * 100:.1f}%")


def cmd_payout(a) -> None:
    matches = _load_matches(a.date)
    legs = _parse_legs(a.legs, matches)
    print(PO.render_text(legs, title=a.title or "组合测算"))
    if a.html:
        spec = [dict(name=L["name"], legs=[dict(L, odd=L["odds"][0], prob=L["probs"][0])])
                for L in [legs]]
        _write_html(a.html, R.ticket_html(
            [dict(name=a.title or "测算票", legs=[dict(L, odd=L["odds"], prob=L["probs"])
                                                 for L in legs])],
            title=a.title or "竞彩足球 · 出票单"))


def cmd_ticket(a) -> None:
    matches = _load_matches(a.date)
    tickets = []
    for i, spec in enumerate(a.assign, 1):
        name, leg_spec = spec.split("=", 1)
        tickets.append(dict(name=name, legs=_parse_legs(leg_spec, matches),
                            multiple=a.multiple))
    html_text = R.ticket_html(tickets, title=a.title or f"竞彩足球 · 出票单 {a.date}",
                              note=a.note)
    _write_html(a.out or f"jc-{a.date.replace('-', '')}-ticket.html", html_text)


def cmd_report(a) -> None:
    matches = _load_matches(a.date)
    leagues = set(a.league.split(",")) if a.league else C.MAIN_LEAGUES
    read_at = None
    payload_path = F.snapshot_path(a.date)
    if payload_path.exists():
        read_at = json.loads(payload_path.read_text(encoding="utf-8")).get("read_at")
    html_text = R.report_html(matches, title=a.title or f"竞彩足球 · {a.date} 赛事分析报告",
                              read_at=read_at, leagues=leagues)
    _write_html(a.out or f"jc-{a.date.replace('-', '')}-report.html", html_text)


def cmd_review(a) -> None:
    s = LD.summary()
    html_text = R.review_html(s, review=("" if not a.points else
                                         "<ul>" + "".join(f"<li>{p}</li>" for p in a.points) + "</ul>"))
    _write_html(a.out or f"jc-review-{s['curve'][-1]['date'].replace('-', '') if s['curve'] else 'empty'}.html",
                html_text)
    print(LD.render_text())


def cmd_ledger(a) -> None:
    if a.action == "show":
        print(LD.render_text())
        for t in LD.all_tickets():
            print(f"  {t['id']:<14}{t['date']}  {t['structure']:<8}{t['cost']:>7.0f} → "
                  f"{t['payout']:>8.2f}  {t['play']}")
    elif a.action == "add":
        rec = json.loads(open(a.file, encoding="utf-8").read())
        print("已登记：", LD.add(rec))
    elif a.action == "settle":
        print("已结算：", LD.settle(a.id, a.payout))


def cmd_info(a) -> None:
    print(f"jc-football v{__import__('jc').__version__}")
    print(f"  包目录    {C.ROOT}")
    print(f"  产出目录  {C.OUTPUTS}")
    print(f"  快照目录  {C.ODDS_DIR}（{len(F.list_snapshots())} 份）")
    print(f"  账本      {C.LEDGER}")
    print(f"  玩法池    {', '.join(f'{k}={v}' for k, v in C.POOLS.items())}")
    print(f"  基准池    {C.BASE_POOL}")


# ---------------------------------------------------------------- 解析

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jc", description="竞彩足球数据与结构测算工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("fetch", help="抓取赔率并落盘快照")
    s.add_argument("--date", default=None)
    s.add_argument("--pools", default=None)
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("snapshots", help="列出快照")
    s.set_defaults(func=cmd_snapshots)

    for name, fn, helptext in [("legs", cmd_legs, "建腿池"),
                               ("scheme", cmd_scheme, "搜索方案")]:
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--date", required=True)
        s.add_argument("--league", default=None)
        if name == "scheme":
            s.add_argument("--legs", type=int, default=None)
            s.add_argument("--rank", default="prof", choices=["prof", "win", "full"])
            s.add_argument("--top", type=int, default=3)
            s.add_argument("--odds-range", default=None)
        s.set_defaults(func=fn)

    s = sub.add_parser("payout", help="测算指定组合回款")
    s.add_argument("--date", required=True)
    s.add_argument("--legs", required=True, help="key:play:pick[+pick],…")
    s.add_argument("--title", default=None)
    s.add_argument("--html", default=None)
    s.set_defaults(func=cmd_payout)

    s = sub.add_parser("ticket", help="生成出票单 HTML")
    s.add_argument("--date", required=True)
    s.add_argument("--assign", nargs="+", required=True, help="票名=key:play:pick,…")
    s.add_argument("--multiple", type=int, default=1)
    s.add_argument("--title", default=None)
    s.add_argument("--note", default="")
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_ticket)

    s = sub.add_parser("report", help="生成分析报告 HTML")
    s.add_argument("--date", required=True)
    s.add_argument("--league", default=None)
    s.add_argument("--title", default=None)
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("review", help="生成复盘报告 HTML")
    s.add_argument("--points", nargs="*", default=[])
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_review)

    s = sub.add_parser("ledger", help="账本读写")
    s.add_argument("action", choices=["show", "add", "settle"])
    s.add_argument("--file", default=None)
    s.add_argument("--id", default=None)
    s.add_argument("--payout", type=float, default=0.0)
    s.set_defaults(func=cmd_ledger)

    s = sub.add_parser("info", help="显示配置")
    s.set_defaults(func=cmd_info)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
