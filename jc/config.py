# -*- coding: utf-8 -*-
"""全局配置：接口地址、玩法池映射、路径、标签。

所有"会变的东西"集中在这里，换玩法/换联赛只改本文件。
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- 路径

PKG_DIR = Path(__file__).resolve().parent          # jc-football/jc
ROOT = PKG_DIR.parent                              # jc-football
TEMPLATES = ROOT / "templates"
KNOWLEDGE = ROOT / "knowledge"
DATA = ROOT / "data"
ODDS_DIR = DATA / "odds"
LEDGER = DATA / "ledger.json"

# 产出目录：默认写到 包根/outputs，可用环境变量覆盖
OUTPUTS = Path(os.environ.get("JC_OUTPUTS", ROOT / "outputs"))

for _d in (DATA, ODDS_DIR, OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 接口

API = "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry"

# 必需请求头：缺 Referer 会被 WAF 拦（403 / 空响应）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://www.sporttery.cn/",
}

# poolCode -> 中文玩法名
POOLS = {
    "had": "胜平负",
    "hhad": "让球胜平负",
    "ttg": "总进球数",
    "hafu": "半全场胜平负",   # 注意是 hafu，不是 bqc
    "crs": "比分",
}

# 基准索引所用的池：实测 ttg 覆盖最全（had 会缺场次）
BASE_POOL = "ttg"

# ---------------------------------------------------------------- 标签

HAD_LABEL = {"h": "主胜", "d": "平", "a": "客胜"}
HHAD_LABEL = {"h": "让球胜", "d": "让球平", "a": "让球负"}
# 让球腿名里已有「让±N」前缀，故用短标签
HHAD_SHORT = {"h": "胜", "d": "平", "a": "负"}
HAFU_LABEL = {
    "hh": "胜/胜", "hd": "胜/平", "ha": "胜/负",
    "dh": "平/胜", "dd": "平/平", "da": "平/负",
    "ah": "负/胜", "ad": "负/平", "aa": "负/负",
}

TTG_TOTAL_LABEL = ["0球", "1球", "2球", "3球", "4球", "5球", "6球", "7+球"]

# 单腿资金投入 = 2 元/注（竞彩固定）
UNIT = 2.0

MAIN_LEAGUES = {"英超", "西甲", "德甲", "意甲", "法甲"}
