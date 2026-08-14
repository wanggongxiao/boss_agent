# BOSS 直聘智能体——详细技术方案

> 版本：v0.2（已评审基线）
> 状态：评审通过，作为开发基线
> 目标目录：`D:\pcapng\boss-agent`

---

## 0. 定位、边界与合规声明（必须先读）

### 0.1 定位

本项目定位为一套 **单账号、低频、辅助个人求职** 的桌面智能体：

- 帮助使用者本人检索 BOSS 直聘上的岗位；
- 读取 JD 与本地简历做匹配评估；
- 在人工有意向的前提下，协助生成并发送首次沟通话术；
- 记录沟通状态，形成求职管理台账。

### 0.2 明确边界（红线）

本项目 **不提供、也不应扩展** 以下能力：

1. 批量注册账号、批量登录多账号；
2. 验证码（极验/滑块/短信）自动破解或绕过；
3. 大规模爬取平台数据或对平台造成访问压力；
4. 批量群发、骚扰式沟通；
5. 盗取、伪造他人身份信息；
6. 绕过支付、会员、面试限制等平台权益。

### 0.3 关于“抗封”的工程化定义

本文档中所有“反侦测 / 拟真”技术，一律重新定义为 **“降低对平台的异常扰动 + 保护本人账号稳定”**：

- 不做隐藏自身为机器人以外用途的欺骗性绕过；
- 拟真行为的首要目标是让自动化动作与“一个真人低频浏览”尽量接近；
- 所有动作保持低频、带随机回退与熔断；
- 任何风控触发（弹窗、验证、行为限制）都 **立即挂起并移交人工**，而不是继续自动突破。

> 说明：BOSS 直聘等平台的自动化行为可能违反其用户协议。使用本项目产生的账号风险由使用者自行承担。建议仅在个人求职的合理频度范围内使用，并遵守平台规则。

---

## 1. 目标与成功标准

### 1.1 业务目标

| 目标 | 说明 |
| --- | --- |
| 岗位检索 | 按设定条件（城市/职位/薪资/经验/学历）检索岗位列表 |
| JD 解析 | 抽取岗位描述、技能要求、硬性条件 |
| 智能匹配 | 结合简历与 JD，输出匹配评分与建议 |
| 沟通决策 | 明确是否主动发起沟通（需人工确认） |
| 话术生成 | 生成个性化首句话术 |
| 状态追踪 | 记录已投递/已读/未读/要微信/面试等状态 |
| 黑名单 | 拦截已拒绝/不匹配的 HR/公司 |

### 1.2 工程成功标准

- 长期运行稳定：支持单次运行 + 常驻模式（受控低频）；
- 兼容性与可维护性：分层清晰，配置与代码分离；
- 可观测性：全链路日志、结构化决策日志；
- 可恢复性：异常挂起后可人工接管并断点续跑；
- 成本可控：先 RAG 粗筛，再 LLM 精判，减少 Token 消耗。

---

## 2. 技术选型总览

| 层次 | 选型 | 说明 |
| --- | --- | --- |
| 语言 / 运行时 | Python 3.11+ | 生态成熟 |
| 包管理 | `pip + venv` | 可复现 |
| 浏览器操控 | **DrissionPage** | 主选，直控内核，免 WebDriver 特征 |
| 备选操控 | Playwright + playwright-stealth | 需要异步并发时启用 |
| Agent 编排 | 自研轻量 FSM + （可选）LangGraph | 先 FSM 保证可控，再评估图编排 |
| 结构化输出 | Pydantic v2 | 强类型校验 |
| LLM | DeepSeek（`deepseek-reasoner` R1 推理 + `deepseek-chat`） | JSON / Function Calling |
| 向量检索 | ChromaDB（本地） | 轻量、零运维起步 |
| 关系存储 | SQLite →（可迁移 PostgreSQL） | 本地起步，后续可替换 |
| 配置 | pydantic-settings + `.env` | 敏感信息不入库 |
| 日志 | loguru | 多 sink、结构化 |
| 通知 | 无（本地日志 + 控制台提示音） | 风控告警与人工接管提醒（不外发） |
| 任务调度 | APScheduler（可选） | 常驻低频巡检 |

---

## 3. 总体架构

```
┌────────────────────────────────────────────────────────────┐
│                    执行控制层（Perception & Execution）        │
│  DrissionPage / CDP                                        │
│  - 会话持久化(user_data_dir)  - 拟真输入(高斯/贝塞尔)          │
│  - DOM/图像风控监听          - 动作熔断与重试                │
└─────────────────────────────▲─────────────────────────────┘
                               │ 动作 / 状态 / 事件
┌─────────────────────────────▼─────────────────────────────┐
│                 智能体控制中枢（Agent Orchestration / FSM）    │
│  节点：检索 → 解析JD → 粗筛(RAG) → 精判(LLM) → 决策 → 沟通      │
│  - 状态机流转   - 异常挂起&报警   - 人工接管(断点续跑)          │
└───────────────▲──────────────────────────────▲──────────────┘
                │ 结构化推理 / 查询               │ 向量 / 状态查询
┌───────────────▼────────────────┐  ┌────────────▼─────────────┐
│       大模型层（DeepSeek API）   │  │    存储层（ChromaDB+SQLite）│
│  - 深度逻辑判断 / 匹配打分         │  │ - 本地 RAG 简历知识库        │
│  - 动态个性化话术生成              │  │ - 历史交互 / 黑名单 / 台账    │
└────────────────────────────────┘  └──────────────────────────┘
```

---

## 4. 目录结构设计

```
boss-agent/
├─ README.md
├─ TECHNICAL_DESIGN.md            # 本文档
├─ pyproject.toml                 # 依赖与工具配置
├─ .env.example                   # 配置样例（真实 .env 不入库）
├─ requirements.txt
├─ requirements-dev.txt
├─ config/
│  ├─ settings.py                 # pydantic-settings 配置
│  ├─ selectors.py                # 页面元素选择器（集中维护，便于页面改版热更新）
│  └─ prompts/
│     ├─ match_prompt.txt         # 匹配打分 Prompt
│     ├─ intro_prompt.txt         # 沟通话术 Prompt
│     └─ system.txt               # 系统角色设定
├─ src/
│  ├─ __init__.py
│  ├─ main.py                     # 入口（CLI + 配置装配）
│  ├─ agent/
│  │  ├─ __init__.py
│  │  ├─ state_machine.py         # FSM 状态机
│  │  ├─ orchestration.py         # 编排器（流程控制）
│  │  ├─ human_loop.py            # 人工接管与信号
│  │  └─ guard.py                 # 熔断 / 限速 / 黑名单守卫
│  ├─ browser/
│  │  ├─ __init__.py
│  │  ├─ page_controller.py       # DrissionPage 封装
│  │  ├─ human_behavior.py        # 高斯延迟 / 贝塞尔轨迹
│  │  ├─ risk_monitor.py          # DOM/图像风控监听
│  │  └─ session.py               # user_data_dir 会话管理
│  ├─ llm/
│  │  ├─ __init__.py
│  │  ├─ client.py                # DeepSeek 客户端封装
│  │  ├─ schemas.py               # Pydantic 结构化输出
│  │  └─ prompt_loader.py
│  ├─ memory/
│  │  ├─ __init__.py
│  │  ├─ vector_store.py          # ChromaDB 封装
│  │  ├─ resume_indexer.py        # 简历切片与向量化
│  │  └─ repo/
│  │     ├─ db.py                 # SQLite 连接与迁移
│  │     ├─ migrations.py
│  │     └─ tables.py             # 数据表定义
│  ├─ pipeline/
│  │  ├─ __init__.py
│  │  ├─ retriever.py             # 岗位列表检索
│  │  ├─ jd_parser.py             # JD 结构化解析
│  │  ├─ matcher.py               # RAG 粗筛 + LLM 精判
│  │  └─ communicator.py          # 沟通动作
│  ├─ notify/
│  │  ├─ __init__.py
│  │  └─ notifier.py              # PushDeer / Server酱 / Telegram
│  └─ utils/
│     ├─ logger.py
│     └─ time_utils.py
├─ data/
│  ├─ resume/                     # 本地简历原始文件
│  ├─ chroma/                     # 向量库持久化
│  └─ sqlite/                     # SQLite 文件
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
└─ scripts/
   ├─ init_db.py
   └─ index_resume.py
```

---

## 5. 执行控制层（浏览器操控）

### 5.1 DrissionPage 封装

- 使用 `ChromiumOptions().set_paths()` 指定本地 Chrome；
- 使用 `set_user_data_path()` 持久化登录态（`user_data_dir`）；
- 通过 CDP 直控，避免 Selenium WebDriver 特征。

```
page_controller.py 职责：
- 启动/恢复浏览器实例
- 页面打开、等待、元素定位
- 表单输入、点击、滚动
- 动作后截取状态快照（文本/DOM/截图）
```

### 5.2 拟真行为（human_behavior.py）

| 能力 | 实现要点 |
| --- | --- |
| 高斯分布延迟 | `random.gauss(mean, sigma)`，禁止固定 `sleep` |
| 贝塞尔轨迹 | 拖拽/鼠标移动用三阶贝塞尔曲线逼近 |
| 打字拟真 | 字符间随机间隔 + 偶发回删重打 |
| 滚动拟真 | 分段滚动 + 随机停顿 |

> 注意：拟真目标是“贴近真人低频行为”，不用于绕过平台对自动化的识别之外的其他目的。

### 5.3 会话持久化（session.py）

- 单一 `user_data_dir`，长期登录态；
- 保存 Cookie/指纹快照；
- 首次运行引导人工扫码/登录，之后尽量复用。

### 5.4 风控监听（risk_monitor.py)

- DOM 层：轮询检测“操作频繁”“验证码”“账号异常”等关键词与弹窗节点；
- 图像层（可选）：OCR/模板匹配辅助判断，默认关闭以降低复杂度；
- 触发后：立即停止自动化动作 → 截图留证 → 通知用户 → 进入人工接管态。

### 5.5 熔断与重试（guard.py）

- 单次运行动作次数上限；
- 连续失败 N 次熔断；
- 指数退避 + 随机抖动；
- 每次“发送沟通”前后强制人工确认/冷却。

---

## 6. 智能体控制中枢（FSM）

### 6.1 状态集合

```
IDLE                # 空闲，等待启动
RETRIEVING          # 检索岗位列表
PARSING_JD          # 解析 JD
COARSE_MATCHING     # RAG 粗筛
FINE_MATCHING       # LLM 精判
DECISION_READY      # 等待人工决策
GENERATING_INTRO    # 生成话术
SENDING             # 发送沟通
WAITING_REPLY       # 等待回复
PAUSED              # 人工接管/风控挂起
STOPPED             # 结束
ERROR               # 异常
```

### 6.2 主流程

```
IDLE → RETRIEVING → PARSING_JD → COARSE_MATCHING
     → FINE_MATCHING → DECISION_READY → (人工确认)
     → GENERATING_INTRO → SENDING → WAITING_REPLY → IDLE
```

### 6.3 异常与降级

- 任何节点异常可进入 `PAUSED`（风控/验证/页面异常）或 `ERROR`（内部错误）；
- `PAUSED` 下等待人工处理后，读取“恢复信号”继续；
- 黑名单/冷却/限速命中时，跳过该目标而非中断整条流水线。

---

## 7. 大模型层（DeepSeek）

### 7.1 客户端封装

- OpenAI 兼容协议，启用 R1 推理：`deepseek-reasoner` 负责匹配打分等重推理任务；
- `deepseek-chat` 作为低延迟话术生成备选；
- 统一封装重试、超时、限流；
- 结构化输出的 JSON Schema 传入。

### 7.2 结构化输出（Pydantic）

```python
class JobEvaluation(BaseModel):
    match_score: int                 # 0-100
    reasons: list[str]               # 匹配/不匹配原因
    should_apply: bool               # 是否发起沟通
    custom_intro: str | None         # 个性化话术

class JdStructured(BaseModel):
    title: str
    skills: list[str]
    hard_requirements: list[str]     # 学历/年限/行业等硬性条件
    soft_requirements: list[str]
    salary_range: str | None
    city: str | None
    company_name: str | None
```

### 7.3 成本控制

- RAG 粗筛先过滤明显不匹配项；
- 仅对“通过粗筛”的 JD 调用 LLM 精判；
- Prompt 精炼、上下文裁剪、结果缓存（同 JD 不重复评估）。

---

## 8. 存储层（记忆）

### 8.1 向量检索（ChromaDB + RAG）

- 简历按「技能 / 项目 / 硬性指标」切片；
- 每个 JD 先与简历向量做余弦相似度粗筛；
- 低于阈值的 JD 直接进入黑名单候选，不再走 LLM。

### 8.2 关系型数据库（SQLite）

核心表设计：

```text
jobs（岗位）
  id, platform_job_id, title, company, hr_id, city,
  salary, jd_text, jd_hash, first_seen_at

evaluations（评估记录）
  id, job_id, match_score, should_apply, reasons_json,
  intro_text, model_version, created_at

conversations（沟通状态）
  id, job_id, hr_id, status(已读/未读/已要微信/面试/拒绝),
  last_message_at, last_interact_at, history_json

blacklist（黑名单）
  id, company, hr_id, reason, added_at

runs（运行记录/审计）
  id, started_at, ended_at, actions_count, risk_events_count

cooldown（冷却）
  id, scope(hr_id/company/target), until_ts, reason
```

---

## 9. 人机协同与异常容错

### 9.1 Human-in-the-Loop

- 凡需 **发起沟通** 的决策，默认需人工确认；
- 提供 CLI/控制台交互回执（如“y / n / skip / pause”）；
- 人工可随时暂停、跳过、接管浏览器操作。

### 9.2 风控告警与通知

本轮不接入外发通知（`NOTIFY_KIND=none`），风控告警方式为：

- 触发验证/限制时：
  1. 挂起 Agent；
  2. 截图/日志留证；
  3. 控制台打印醒目告警 + 本地播放提示音；
- 人工在浏览器完成验证后，控制台输入恢复指令，Agent 续跑；
- `notify/notifier.py` 保留通知接口，后续需要时再接入 PushDeer / Server酱 / Telegram。

### 9.3 断点续跑

- 每次处理都用 `job_hash` + 状态落库；
- 重跑时跳过已完成/已入黑名单目标。

---

## 10. 风控 / 安全 / 限速策略（生产级核心）

| 策略 | 说明 |
| --- | --- |
| 单账号 | 仅支持个人单账号，禁止多账号 |
| 低频 | 全局最小动作间隔 + 每日沟通上限 |
| 冷却 | 对同一 HR/公司/岗位去重与冷却 |
| 黑名单 | 拒绝/不匹配/失败目标直接拦截 |
| 熔断 | 连续失败即熔断，进入人工接管 |
| 脱敏 | 账密/Token 只存 `.env`，不入库、不进日志 |
| 审计 | 每次动作、每个决策落库可追溯 |
| 分档限速 | `conservative`=20/天(默认) / `normal`=50/天 / `aggressive`=200/天(需显式确认) |

---

## 11. 配置管理

```ini
# .env.example
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-reasoner   # 重推理/匹配打分；低延迟话术用 deepseek-chat

BROWSER_USER_DATA_DIR=./data/browser_profile

DB_PATH=./data/sqlite/boss.db
CHROMA_DIR=./data/chroma

NOTIFY_KIND=none                  # 本轮固定 none，不外发通知

AGENT_SAFETY_TIER=conservative    # conservative(20/天,默认) | normal(50/天) | aggressive(200/天)
AGENT_DAILY_SEND_LIMIT=200        # 配置上限；实际按 AGENT_SAFETY_TIER 生效
AGENT_GLOBAL_MIN_INTERVAL_S=45    # 全局最小动作间隔，实际 ±15s 高斯抖动
AGENT_COOLDOWN_SAME_TARGET_D=7
```

---

## 12. 分阶段实施路线图

| 阶段 | 内容 | 交付物 |
| --- | --- | --- |
| P0 | 项目骨架、配置、日志、DB 迁移 | 可初始化、可空跑 |
| P1 | DrissionPage 会话 + 页面封装 + 拟真行为 | 能登录并读取首页 |
| P2 | 岗位检索 + JD 解析 | 可导出结构化 JD |
| P3 | 简历向量化 + RAG 粗筛 | 本地召回 |
| P4 | DeepSeek 结构化匹配 + 话术生成 | 可打分/出话术 |
| P5 | FSM 编排 + 人工确认 + 沟通动作 | 端到端最小闭环 |
| P6 | 风控监听 + 通知 + 断点续跑 | 生产级稳定性 |
| P7 | 黑名单/冷却/审计 + 测试 | 加固与验收 |

优先落地 **P0 → P2 → P5（最小闭环）**，再补 RAG 与风控加固。

---

## 13. 测试与验证策略

- 单元测试：状态机、结构化解析、限速/冷却逻辑；
- 集成测试：用录制的页面 fixture 模拟检索与 JD 解析；
- 干跑模式（dry-run）：不真正发送沟通，只走决策链路；
- 验收标准：单账号低频可运行、异常可挂起、可断点续跑、可审计。

---

## 14. 风险与注意事项

1. **平台协议风险**：自动化可能违反用户协议，存在封号可能，务必低频、保守；
2. **页面改版**：选择器集中配置（`config/selectors.py`），便于热更新；
3. **风控升级**：若平台升级验证策略，本项目只支持“挂起+人工”，不做自动破解；
4. **法律合规**：不采集、不外发他人个人信息；仅用于本人求职；
5. **LLM 幻觉**：话术发送前必须人工确认，避免虚假信息。

---

## 15. 本方案评审确认点

- [x] 目标目录确认为 `D:\pcapng\boss-agent`
- [x] Python 版本与包管理工具：pip（`requirements.txt` + `requirements-dev.txt`）
- [x] 浏览器主选 DrissionPage，Playwright + playwright-stealth 作为备选
- [x] LLM 使用 DeepSeek，启用 R1 推理（`deepseek-reasoner`）
- [x] 通知渠道：无（仅本地日志 + 控制台提示音）
- [x] 每日沟通上限 200（配置上限，分档生效）；全局最小间隔 45s（±15s 高斯抖动）
