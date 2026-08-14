# boss-agent

个人求职辅助智能体：检索 BOSS 直聘岗位、评估岗位与简历匹配度、在人工确认下辅助发起首次沟通，并追踪沟通状态。

> 项目定位、边界与架构详见 [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md)。

---

## 一、环境要求

- Python 3.11+
- 本地 Chrome（程序通过 CDP 直控，需已安装 Chrome）
- （可选）DeepSeek API Key，用于匹配打分与话术生成

---

## 二、首次安装（Windows PowerShell）

在项目目录下执行：

```powershell
cd D:\pcapng\boss-agent

# 1. 创建虚拟环境并激活
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt
```

---

## 三、配置

```powershell
# 复制配置样例为真实配置
Copy-Item .env.example .env
```

编辑 `.env`，至少填入：

```ini
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

其它可保持默认。

---

## 四、准备简历

把简历保存为纯文本，例如放到 `data\resume\resume.txt`（内容可以是技能、项目经历、工作经历等）。

---

## 五、初始化数据库

```powershell
python scripts\init_db.py
```

---

## 六、运行

### 1. 干跑（推荐先这样，不会真的发消息）

```powershell
python -m src.main --resume data\resume\resume.txt
```

按关键词搜索岗位（`--keyword` 可重复传入）：

```powershell
python -m src.main --keyword "C++开发工程师" --limit 10

python -m src.main `
  --keyword "机器人算法工程师" `
  --keyword "运动控制算法工程师" `
  --limit 10
```

多个关键词的结果会按岗位 ID 自动去重；未传 `--keyword` 时继续使用页面默认推荐岗位。

干跑会真实打开浏览器、检索岗位、解析 JD、调用 LLM 打分并预览话术，但 **不会发送** 任何消息。

### 2. 真实发送（会逐条人工确认）

```powershell
python -m src.main --resume data\resume\resume.txt --live
```

- 每条沟通前都会在控制台打印岗位和话术，并要求你输入确认：
  - `y` = 发送
  - `n` = 跳过
  - `q` = 退出整个程序
- 即使加 `--live`，也会受限速/冷却/每日上限保护，不会失控。

---

## 七、首次登录

第一次运行时程序会打开 Chrome，你需要在弹出的浏览器里完成一次 BOSS 直聘登录（扫码或密码）。登录态会持久化到 `data\browser_profile`，后续运行会自动复用，无需反复登录。

若长期不用后需要重新登录，删除 `data\browser_profile` 目录再运行即可。

---

## 八、重要：页面选择器校准（首次真实使用前必做）

`config\selectors.py` 中的元素选择器目前是**占位值**，BOSS 直聘页面结构可能不同。在真实抓取前，需要：

1. 用浏览器打开 BOSS 直聘岗位列表页和详情页；
2. 按 F12 查看实际 DOM，确认岗位卡片、标题、公司、薪资、JD 文本、沟通按钮等元素的选择器；
3. 把对应选择器更新到 `config\selectors.py`。

否则检索/解析可能返回空，或沟通按钮找不到。

---

## 九、限速与保护

- 分档限速（`.env` 中 `AGENT_SAFETY_TIER`）：
  - `conservative`：20/天（默认）
  - `normal`：50/天
  - `aggressive`：200/天（需显式选择并接受风险）
- 全局最小动作间隔 45s（±15s 高斯抖动）。
- 同一公司/HR 7 天冷却。
- 连续失败 5 次熔断，触发验证码/异常时挂起并本地告警，不做自动绕过。

> 自动化行为可能违反 BOSS 直聘用户协议，存在封号风险。请仅在个人求职的合理频度内使用，并遵守平台规则。

---

## 十、测试

```powershell
pip install -r requirements-dev.txt
python -m pytest tests\test_state_machine.py -q
```

---

## 当前进度

- [x] P0 项目骨架 + 配置 + 日志 + SQLite 迁移
- [x] P1 DrissionPage 会话/页面封装/拟真行为
- [x] P2 岗位检索 + JD 解析
- [x] P3 简历向量化 + RAG 粗筛
- [x] P4 DeepSeek 结构化匹配 + 话术生成
- [x] P5 FSM 编排 + 人工确认 + 沟通（最小闭环）
- [x] P6 风控监听 + 熔断 + 断点续跑
- [x] P7 黑名单/冷却/审计 + 测试
