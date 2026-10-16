# 换机器安装（5 步）

目标：在新机器上 5 分钟内恢复完整能力（脚本 + 技能 + 专家 + 数据）。

## 步骤

### 1. 拿到包

```bash
git clone <你的仓库地址> jc-football
cd jc-football
```

### 2. 装成技能（实现"一句话触发"）

把整个目录拷到 WorkBuddy 的技能目录：

```bash
# 用户级（所有项目可用）
cp -r . ~/.workbuddy/skills/jc-football

# 或 项目级（只在该工作区可用）
cp -r . "{工作区}/.workbuddy/skills/jc-football"
```

> Windows 用 `xcopy /E /I . "%USERPROFILE%\.workbuddy\skills\jc-football"`。
> 拷进去后，说"分析今晚的英超"即会自动加载本技能。

### 3. 注册专家包

专家包在 `expert/`，知识本体是 `expert/agents/jc-football-analyst.md`。
**`plugin.json` 的 `name`/`agentName`、目录名、`agents/` 下的文件名都不可改**（改了专家会丢失）。

```bash
EXPERT_MANAGER="<WorkBuddy 内置>/skills/expert-manager/scripts"
python "$EXPERT_MANAGER/validate_expert.py" expert
python "$EXPERT_MANAGER/register_expert.py" expert
```

### 4. 首跑自检

```bash
python -m jc fetch                 # 抓数 + 落盘快照
python -m jc legs --date <今天>     # 建腿池
python -m jc info                  # 看路径与快照数
```

**必须确认三件事**：
1. `fetch` 五个池都返回场次数（有 403 就是请求头被拦，检查 UA + Referer）。
2. `had` 池场次数**可能少于**其它池 —— 这是已知现象，基准索引用 `ttg`。
3. 快照写进了 `data/odds/YYYY-MM-DD.json`，且带 `read_at` 时间戳。

### 5. 恢复历史（可选）

```bash
python scripts/seed_ledger.py      # 录入历史实购票 → data/ledger.json
python -m jc review                # 生成复盘报告
```

## 卸载

删掉技能目录（`~/.workbuddy/skills/jc-football`）并注销专家包即可，不影响其它项目。

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `fetch` 返回 403 / 空 | 缺 `User-Agent` 或 `Referer` | 改 `jc/config.py` 的 `HEADERS` |
| 只有第一场有赔率、其余全空 | 跨池 `dict.update()` 覆盖 | 用 `odds.merge_match()`，不要自己写合并 |
| 某场在某玩法查不到 | `had` 池缺场次是已知现象 | 用 `--league` 过滤后核对，基准取自 `ttg` |
| 复盘时赔率对不上 | 未在赛前存快照，过期场次接口不再返赔率 | 以后**每次赛前必跑 `jc fetch`** |
| 专家装上后名字变了/丢失 | 改了 `plugin.json` 的 name/agentName 或目录名 | 恢复原名重装 |
