# -*- coding: utf-8 -*-
"""从专家包同步知识库到 knowledge/，保证"规则只有一份源头"。

专家包是**知识唯一源头**；本脚本把其中的铁律 / 经验库 / 自检清单 / 数据接口
抽取成独立文件，供 CLI、SKILL.md、他人阅读。改规则只改专家包，再跑本脚本。

用法：
    python scripts/sync_knowledge.py [专家包路径]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT_EXPERT = Path(
    r"C:\Users\lee\.workbuddy\plugins\marketplaces\my-experts\plugins\jc-football-analyst"
)
ROOT = Path(__file__).resolve().parents[1]
KNOW = ROOT / "knowledge"


def slice_section(lines: list, start_pat: str, end_pat: str) -> str:
    """截取从匹配 start_pat 的行起、到匹配 end_pat 的行之前的内容。"""
    i = next((n for n, L in enumerate(lines) if re.match(start_pat, L)), None)
    if i is None:
        return ""
    j = next((n for n in range(i + 1, len(lines)) if re.match(end_pat, lines[n])), len(lines))
    return "".join(lines[i:j]).rstrip() + "\n"


def main() -> None:
    expert = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXPERT
    md = expert / "agents" / "jc-football-analyst.md"
    if not md.exists():
        print(f"找不到专家本体：{md}")
        sys.exit(1)
    lines = md.read_text(encoding="utf-8").splitlines(keepends=True)
    KNOW.mkdir(parents=True, exist_ok=True)

    parts = {
        "铁律.md": (
            "# 复盘校准铁律（地基校验层）\n\n"
            "> 自动同步自专家包 `agents/jc-football-analyst.md` §4.5。**只在专家包改，改完跑 "
            "`scripts/sync_knowledge.py`。**\n\n",
            r"^### 4\.5", r"^### 4\.6",
        ),
        "经验库.md": (
            "# 实战经验库（滚动更新）\n\n"
            "> 自动同步自专家包 §10。L 编号为经验条目，⑯⑰ 等为自检清单项。\n\n",
            r"^### 10\.1", r"^### 10\.2",
        ),
        "案例记录.md": (
            "# 案例记录（按时间倒序）\n\n> 自动同步自专家包 §10.2。\n\n",
            r"^### 10\.2", r"^### 10\.3",
        ),
        "自检清单.md": (
            "# 出票前自检清单\n\n> 自动同步自专家包 §10.3。\n\n",
            r"^### 10\.3", r"^## 十一|^### 10\.4|\Z",
        ),
        "数据接口.md": (
            "# 竞彩官方数据接口速查\n\n> 自动同步自专家包 §2.3.1 / §2.4。\n\n",
            r"^#### 2\.3\.1", r"^### 2\.5|^## 三、",
        ),
    }

    for fname, (header, a, b) in parts.items():
        body = slice_section(lines, a, b)
        if not body:
            print(f"  ! 未匹配到 {a}（跳过 {fname}）")
            continue
        # 把 ### 4.5 / ### 10.1 这类标题降一级，避免与文件 H1 冲突
        body = re.sub(r"^### ", "## ", body, flags=re.M)
        (KNOW / fname).write_text(header + body, encoding="utf-8")
        print(f"  ✓ {fname}  {len(body)} 字")

    print(f"知识库已同步至 {KNOW}")


if __name__ == "__main__":
    main()
