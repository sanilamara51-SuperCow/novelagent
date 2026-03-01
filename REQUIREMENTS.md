# 通用小说编排智能体系统 — 需求规格 v2

> 本文档供 Claude Code 实例阅读，用于理解和实现本系统。
> 当前代码库是面向北魏历史小说的原型，本文档定义其通用化重构方案。

## 1. 系统定位

一个 Director 驱动的多智能体长篇小说生成系统。

核心理念：**Director 是大脑，7 个 Agent 是手脚**。Director 负责全局思考和战略决策，Agent 负责执行具体任务。复杂的编排逻辑从代码转移到 LLM 推理。

不绑定任何题材。历史、玄幻、都市、科幻、悬疑均可，通过配置和 prompt 模板切换。

## 2. 架构

### 2.1 核心分层

```
┌─────────────────────────────────────────────────┐
│  Director（总控规划官）— 有 LLM 大脑             │
│  理解全局 → 战前分析 → 生成 WritingBrief         │
│  审视节奏 → 管理伏笔 → 协调多线 → 微调大纲       │
└──────────────────┬──────────────────────────────┘
                   │ WritingBrief + QA 重点
                   ▼
┌─────────────────────────────────────────────────┐
│  Pipeline（可组合的质检流水线）                    │
│  Writer → ConsistencyChecker → StylePolisher     │
│        → EmotionRiskControl → MemoryUpdate       │
└─────────────────────────────────────────────────┘
```

### 2.2 双模式

**模式 A：独立部署（Standalone）**
```
用户 ←→ Director CLI ←→ Director Agent (LLM) ←→ Pipeline ←→ [7 Agents]
                                    ↕
                          MemoryManager + Storage
```
- Director 是一个有 LLM 大脑的 Agent，通过 CLI 与用户对话
- 用户可以用自然语言跟 Director 讨论创作方向、审查结果、调整策略
- 也支持命令式操作（`/write 1-10`、`/status`）

**模式 B：Claude Skills 集成**
```
用户 ←→ Claude (= Director) ←→ Skills/Tools ←→ [7 Agents]
                                    ↕
                          MemoryManager + Storage
```
- Claude 自身就是 Director，天然具备全局推理能力
- 每个 Agent 封装为 skill/tool
- Director 的逻辑就是 Claude 的推理过程

**关键洞察**：Director = Claude = Skill 使用者，三者是同一个角色。

### 2.3 共享层（两种模式复用）

- `BaseAgent` 及所有 Agent 实现
- `Pipeline` + `Stage` 抽象
- `MemoryManager`（含伏笔账本、节奏追踪）
- `NovelStorage`（持久化）
- `RAGRetriever`（知识检索）
- `ContextAssembler`（智能上下文压缩）
- 数据模型（Pydantic v2）
- Prompt 模板体系

## 3. Director（总控规划官）

### 3.1 为什么需要 Director

当前 Orchestrator 是个"调度员"——按固定顺序调 Agent，不会"思考"。真正缺的是一个有智能的战略层。

| | Orchestrator（当前） | Director（新） |
|---|---|---|
| 智能 | 无，纯代码逻辑 | 有，每章前做一次 LLM 推理 |
| 输入 | 状态机当前状态 | 全局小说状态：大纲进度、伏笔账本、节奏曲线、角色弧线 |
| 输出 | "下一步调哪个 Agent" | WritingBrief + QA 重点 + 可选的大纲微调 |
| 决策 | 无 | "大纲说这章是过渡，但前两章都是过渡，需要加速" |

### 3.2 Director 的职责

每章开写前，Director 做一次"战前分析"：

```
Director.plan_chapter(chapter_number) → ChapterPlan:

  1. 审视全局
     - 大纲完成度：30/200章
     - 节奏曲线：[3, 5, 8, 4, 7, ...] → "前两章偏高，这章该回落"
     - 伏笔状态：3个已埋未收，1个即将到期
     - 多线进展：主线在ch28，暗线在ch25，差距过大需要补
     - 读者认知负荷：上章引入了3个新角色，本章不宜再加

  2. 生成 WritingBrief（给 Writer，见 3.3）

  3. 生成 QA 重点（给质检 pipeline）
     - ConsistencyChecker: "重点检查角色X的立场转变是否有铺垫"
     - EmotionRiskControl: "本章目标 tension=4，不要超过6"
     - StylePolisher: "上一章对话太多，本章增加环境描写比例"

  4. 可选：微调大纲
     - "原大纲这章是纯过渡，但节奏需要，加一个小冲突"
     - 记录偏差，后续章节可能需要调整
```

### 3.3 WritingBrief（写作简报）

Director 的核心输出。解决"Writer 被撑死"的问题——把全局信息压缩成精炼指令。

```
WritingBrief:
  # 基本任务
  chapter_outline: str          # 本章大纲（精简版）
  opening_hook: str             # "上章悬念：读者最想知道XXX，本章开头必须回应"
  closing_hook: str             # "本章结尾需要制造的悬念"

  # 伏笔指令（2-3条，不多）
  foreshadowing:
    plant: ["在对话中暗示X的真实身份"]
    payoff: ["回收ch3埋的火药线索"]

  # 角色指令（只含本章出场角色）
  characters:
    - name: "尔朱荣"
      current_state: "刚打完胜仗，志得意满"
      voice: "短句、军令式、偶尔粗口"
      knows: ["魏铭有奇术"]
      doesnt_know: ["魏铭来自未来"]

  # 场景约束
  scenes:
    - "军帐议事：3人对话，信息博弈"
    - "夜间独白：主角内心戏"

  # 衔接
  previous_ending: str          # 上章最后200字
  thread_context: str           # "本章主线，暗线进展到：..."

  # 节奏指令
  target_tension: int           # Director 根据全局节奏设定
  sensory_focus: str            # "上章视觉为主，本章多用听觉和嗅觉"
```

信息流：`全局状态（很大）→ Director（LLM 压缩+推理）→ WritingBrief（~1500 tokens）→ Writer（只管写）`

### 3.4 Director 的成本

- 输入：全局摘要 + 伏笔账本 + 节奏序列 + 当前大纲 ≈ 3000-4000 tokens
- 输出：WritingBrief + QA 重点 ≈ 2000 tokens
- 用中等模型即可，不需要最强模型
- 每章多一次 LLM 调用，换来真正有智能的编排

### 3.5 Skills 模式下

Director 就是 Claude 自己。用户说"写下一章"，Claude 自然会：
1. 回顾创作状态（读取记忆和伏笔账本）
2. 思考这章该怎么写（Director 推理）
3. 生成 brief 调用 Writer skill
4. 审查结果，决定是否需要修改

## 4. Pipeline（可组合流水线）

### 4.1 设计理念

当前 Orchestrator 把所有逻辑塞在一个类里。章节生成的质检流水线其实是固定模式，应该拆成可组合的 Pipeline。

```python
chapter_pipeline = Pipeline([
    WriteStage(writer_agent),
    DebateStage(debater_agent, condition=lambda ctx: ctx.outline.requires_debate),
    ConsistencyStage(checker_agent, max_retries=2),
    PolishStage(polisher_agent),
    RiskStage(risk_agent),
])

result = await chapter_pipeline.run(context)
```

### 4.2 Stage 接口

```python
class Stage(ABC):
    name: str
    condition: Callable | None    # 可选的前置条件，返回 False 则跳过
    max_retries: int = 1

    async def execute(self, context: PipelineContext) -> StageResult
    async def on_failure(self, context: PipelineContext, error: Exception) -> FailureAction
```

`StageResult`:
- `success: bool`
- `output: Any`
- `should_retry_previous: bool` — 如 ConsistencyChecker 失败，回退到 Writer 重写
- `metadata: Dict`

### 4.3 好处

- 每个 Stage 独立可测试
- 可按题材配置不同 pipeline（轻量模式跳过 polish）
- 重试逻辑内聚在 Stage 内部
- 新增质检环节只需加一个 Stage
- Middleware 机制处理横切关注点（见 4.4）

### 4.4 Middleware

token 统计、日志、重试、超时不应该每个 Agent 自己写：

```python
agent = WriterAgent(config)
agent = with_retry(agent, max_retries=2)
agent = with_timeout(agent, seconds=600)
agent = with_token_tracking(agent)
```

## 5. 状态管理（简化）

### 5.1 项目级状态（5 个，替代原 13 个）

```
init → world_built → outlined → writing → completed
```

章节内部步骤（consistency_check、style_polish 等）由 Pipeline 内部管理，不再是全局状态。

### 5.2 断点续写

靠 `Storage.list_chapters()` 判断进度，比状态机更可靠：
- 有 world_setting.json → world_built
- 有 outline.json → outlined
- 有 N 个 chapter.md → writing, 已完成 N 章
- N == total_chapters → completed

### 5.3 持久化

项目状态存在 `novel_state.json`，包含：
- `status: str` — 5 个状态之一
- `current_chapter: int` — 当前进度
- `created_at / updated_at`
- `genre_config_ref: str` — 指向 genre_config.yaml

## 6. 七个执行智能体

### 6.1 Agent 协议

```python
class BaseAgent(ABC):
    name: str
    system_prompt: str          # 从 config/prompts/{genre}/{name}.txt 加载
    config: AgentConfig         # 从 settings.yaml 加载

    async def process(self, input: AgentInput) -> AgentOutput
```

**AgentInput**: task_type, context, instruction, metadata
**AgentOutput**: agent_name, success, content, metadata, token_usage

### 6.2 WorldBuilder（世界构建）

**输入**：用户描述 + GenreConfig + RAG 结果（如有）

**输出**：`WorldSetting` JSON — 包含 era, political/power_system, geography, key_events（标记 changeable/immutable）, factions, notable_figures（含 CharacterVoice）, protagonist, main_plot, story_threads

**新增**：创建角色时同步生成 CharacterVoice（见 8.2）

### 6.3 PlotDesigner（大纲设计）

**输入**：WorldSetting + 用户偏好（卷数、章数、节奏）

**输出**：`Outline` JSON
- volumes → chapters 层级
- 每章：title, summary, key_scenes, involved_characters, emotional_arc
- 标记 `requires_debate: true` 的章节
- 每卷独立 emotional_theme

**新增**：
- 规划伏笔的埋设和回收（ForeshadowingPlan，见 8.1）
- 规划多线叙事交织（StoryThreads，见 8.4）
- 规划全局节奏曲线（target_tension per chapter）

### 6.4 Writer（写作）

**输入**：WritingBrief（由 Director 通过 ContextAssembler 生成，~1500 tokens）

Writer 不再接收 10 个组件的拼接，而是一份精炼的写作简报。思考在 Director 做完，审查在后处理做完，Writer 只管写。

**输出**：Markdown 章节正文（字数由 GenreConfig 控制）

**max_tokens 调整**：当前 3072 太小（中文约 1.5-2 token/字，写 3000-5000 字需要 4500-10000 tokens），建议至少 8192。

### 6.5 SandboxDebater（沙盘推演）

**输入**：DebateConfig（topic, participants, max_rounds）+ 背景上下文

**输出**：`DebateResult` — transcript, outcome, character_changes

**机制**：每轮 NPC 并发生成发言，终止条件：共识/最大轮数/重复检测

### 6.6 ConsistencyChecker（一致性校验）

**输入**：章节正文 + ChapterOutline + 上下文 + Director 的 QA 重点

**输出**：`ConsistencyReport` — issues (type/severity/description/suggestion), passed

**校验维度**（由 GenreConfig.consistency_rules 控制）：
- `timeline`、`character`、`geography`
- `history_accuracy`（仅历史）、`power_system`（仅玄幻/科幻）
- **新增** `foreshadowing`：到期伏笔是否回收
- **新增** `thread_continuity`：多线叙事连贯性
- 可扩展自定义规则

### 6.7 StylePolisher（风格润色 → 文学质检）

**输入**：章节正文 + 风格指南 + Director 的 QA 重点

**输出**：润色后正文 + metadata

**扩展检查项**：
- 感官维度覆盖（至少 3 种，不能全是视觉）
- 对话区分度（不同角色说话方式是否有差异）
- 环境描写与对话的比例
- AI 指纹检测（破折号滥用、解释性填充句）

### 6.8 EmotionRiskControl（情绪风控）

**输入**：章节正文 + ChapterOutline + **前 N 章 tension_score 序列** + Director 的 QA 重点

**输出**：`RiskReport`
- 四维评分（1-10）：tension_score, villain_iq, protagonist_difficulty, arc_match
- **新增** `reader_proxy` 维度：
  - 信息过载检测（一章引入太多新角色/势力）
  - 悬念驱动力（是否足够驱动翻页）
  - 读者对主角的情感倾向（同情/崇拜/厌烦）
  - 困惑点检测（"为什么这个角色要这么做"）
- **新增** `rhythm_check`：对比前 N 章节奏，判断全局节奏合理性
- rewrite_required: bool
- suggestions

## 7. 记忆系统

### 7.1 短期记忆（ShortTermMemory）

- 滑动窗口，保留最近 N 章摘要（默认 N=3）
- `deque[ChapterSummary]`，内存维护
- `get_context_string(max_tokens)` / `get_last_chapter_ending()`
- Token 估算：中文 `len(text) // 2`

### 7.2 长期记忆（LongTermMemory）

SQLite 持久化，每个项目独立 `memory.sqlite`，WAL 模式。

**原有表**：
- `characters`：角色当前状态（JSON）
- `events`：章节事件日志
- `timeline`：时间线事件
- `relationships`：角色关系图

**新增表**：
- `foreshadowing`：伏笔账本（见 8.1）
- `rhythm`：节奏序列（见 8.3）
- `threads`：多线叙事状态（见 8.4）

### 7.3 摘要器（Summarizer）

LLM 驱动，从章节正文提取结构化 `ChapterSummary`：
- core_events, character_changes, key_dialogues
- turning_points, cliffhangers, timeline_events
- **新增** foreshadowing_planted, foreshadowing_paid_off
- **新增** sensory_dimensions_used（视/听/嗅/触/味）

JSON 解析容错：直接解析 → 代码块提取 → 正则兜底

### 7.4 MemoryManager（协调器）

每章写完后的更新流程：
```
章节正文 → Summarizer → ChapterSummary
  ├→ STM.add_summary()
  ├→ LTM.update_character() × N
  ├→ LTM.mark_timeline() × N
  ├→ LTM.update_foreshadowing()     # 新增
  ├→ LTM.record_tension(score)      # 新增
  ├→ LTM.update_thread_progress()   # 新增
  ├→ Storage.save_summary()
  └→ RAG.index_chapter()（可选）
```

**记忆更新异步化**：写完章节立即返回给用户/Director，记忆更新在后台跑。

## 8. 新增核心模块

### 8.1 ForeshadowingLedger（伏笔账本）

当前系统最大的缺口。长篇小说最致命的问题是伏笔烂尾。

```
Foreshadow:
  foreshadow_id: str
  description: str              # 伏笔内容
  planted_chapter: int          # 埋设章节
  expected_payoff_range: [int, int]  # 预期回收范围
  payoff_chapter: int | None    # 实际回收章节
  status: planted | paid_off | overdue | abandoned
  importance: major | minor     # 主线伏笔 vs 细节伏笔
  related_characters: List[str]
```

**生命周期**：
- PlotDesigner 在大纲阶段批量规划（ForeshadowingPlan）
- Director 每章检查到期伏笔，写入 WritingBrief
- Writer 按指令埋设/回收
- Summarizer 提取实际埋设/回收的伏笔
- ConsistencyChecker 审计：到期未回收 → warning，严重过期 → error
- MemoryManager 更新状态

### 8.2 CharacterVoice（角色语音卡）

解决"千人一面"问题。嵌入 Character 数据模型。

```
CharacterVoice:
  speech_pattern: str       # "短句、粗口、军事术语"
  verbal_tics: List[str]    # 口头禅 ["哼"、"末将以为"]
  vocabulary_level: str     # "粗俗" | "文雅" | "学究" | "市井"
  sentence_length: str      # "极短" | "短" | "中" | "长"
  emotional_expression: str # "内敛" | "外放" | "压抑"
```

- WorldBuilder 创建角色时生成
- Director/ContextAssembler 只提取本章出场角色的语音卡注入 WritingBrief
- StylePolisher 检查对话区分度

### 8.3 RhythmTracker（节奏追踪）

解决"只看单章不看全局"的问题。

- LTM 新增 `rhythm` 表，记录每章 tension_score
- Director 每章前读取序列，判断节奏走向
- EmotionRiskControl 对比前 N 章，检测：
  - 连续 3 章高潮 → 建议降节奏
  - 连续 3 章铺垫 → 建议加速
  - 节奏单调（方差过小）→ 建议制造波动

### 8.4 StoryThreads（多线叙事）

长篇小说常有 2-3 条故事线交织。

```
StoryThread:
  thread_id: str
  name: str                 # "主角崛起线" | "宫廷阴谋线"
  chapters: List[int]       # 涉及章节
  pov_character: str        # 视角角色
  arc: str                  # 整体弧线描述
  current_progress: int     # 最新推进到的章节
```

- PlotDesigner 设计大纲时规划多线交织
- Director 每章告诉 Writer 当前属于哪条线、其他线进展到哪
- ConsistencyChecker 检查线程连贯性

### 8.5 InformationAsymmetry（信息不对称表）

让对话有"潜台词"和"言外之意"。

Director 为每个场景生成信息不对称表，注入 WritingBrief：

```
信息不对称:
  - 魏铭知道河阴之变即将发生，尔朱荣不知道魏铭知道
  - 元子攸知道尔朱荣有反心，但不知道魏铭在暗中布局
```

Writer 据此让角色"说漏嘴"或"故意隐瞒"，对话自然产生张力。

不需要独立 Agent，是 Director 推理的一部分。

## 9. 上下文组装（ContextAssembler）

### 9.1 从"机械拼接"到"智能压缩"

当前 ContextAssembler 把 10 个组件拼在一起塞给 Writer，导致 Writer 注意力分散。

改造后：ContextAssembler 用一次轻量 LLM 调用，把所有原始信息压缩成 WritingBrief。

```
原始信息（~8000 tokens）:
  世界观全文 + 大纲 + 角色状态 + 近章摘要 + 伏笔账本 + RAG + ...
      ↓ LLM 压缩（用便宜模型）
  WritingBrief（~1500 tokens）
      ↓
  Writer prompt（~2000 tokens total）
```

### 9.2 各 Agent 的上下文

| Agent | 上下文来源 |
|-------|-----------|
| Director | 全局摘要 + 伏笔账本 + 节奏序列 + 当前大纲 + 多线状态 |
| Writer | WritingBrief（Director 输出，经 ContextAssembler 压缩） |
| ConsistencyChecker | 章节正文 + 大纲 + 近章摘要 + 角色状态 + 世界观 + Director QA 重点 |
| StylePolisher | 章节正文 + 风格指南 + 上章风格参考 + Director QA 重点 |
| EmotionRiskControl | 章节正文 + 大纲 + tension 序列 + Director QA 重点 |
| SandboxDebater | topic + NPC 列表（含 CharacterVoice）+ 背景上下文 |
| WorldBuilder | 用户描述 + GenreConfig + RAG 结果 |
| PlotDesigner | WorldSetting + 用户偏好 |

## 10. 数据模型（Pydantic v2）

### 10.1 世界观层

```
WorldSetting
├── era: str
├── year_range: Tuple[int, int] | None
├── political_system: str        # 或 power_system（玄幻）
├── social_structure: str
├── geography: Dict[str, Any]
├── key_events: List[HistoricalEvent]
│   └── year, event, description, changeable: bool
├── factions: List[Faction]
│   └── name, leader, stance, strength
├── notable_figures: List[Figure]
│   └── name, identity, personality, current_position, voice: CharacterVoice
├── protagonist: Dict[str, Any]
├── main_plot: Dict[str, Any]
└── story_threads: List[StoryThread]    # 新增
```

### 10.2 大纲层

```
Outline
├── title, total_chapters, main_storyline, core_conflict, protagonist_arc
├── foreshadowing_plan: List[Foreshadow]    # 新增
├── rhythm_curve: List[int]                  # 新增：每章目标 tension
└── volumes: List[Volume]
    ├── volume_number, title, summary, emotional_theme
    └── chapters: List[ChapterOutline]
        ├── chapter_id, number, title, summary
        ├── key_scenes: List[Scene]
        ├── involved_characters: List[str]
        ├── emotional_arc: EmotionalArc
        ├── target_tension: int              # 新增
        ├── active_thread: str               # 新增：本章主线程
        ├── requires_debate: bool
        └── debate_config: DebateConfig | None
```

### 10.3 角色层

```
Character
├── character_id, name, aliases: List[str]
├── identity, personality, background
├── goals: List[str]
├── relationships: Dict[str, str]
├── voice: CharacterVoice                    # 新增
├── status: CharacterStatus
│   └── chapter_id, location, position, health, mood, key_info
└── history: List[CharacterEvent]
```

### 10.4 Director 输出层

```
ChapterPlan
├── chapter_number: int
├── writing_brief: WritingBrief
├── qa_focus: QAFocus
│   ├── consistency_focus: List[str]
│   ├── style_focus: List[str]
│   └── risk_focus: List[str]
├── outline_adjustments: List[str] | None
└── director_notes: str                      # 给自己的备忘

WritingBrief
├── chapter_outline: str
├── opening_hook: str
├── closing_hook: str
├── foreshadowing: ForeshadowingDirective
│   ├── plant: List[str]
│   └── payoff: List[str]
├── characters: List[CharacterBrief]
│   └── name, current_state, voice_summary, knows, doesnt_know
├── scenes: List[str]
├── previous_ending: str
├── thread_context: str
├── target_tension: int
├── sensory_focus: str
└── information_asymmetry: List[str]
```

### 10.5 Agent 输出层

```
ChapterSummary
├── chapter_id, core_events, character_changes
├── key_dialogues, turning_points, cliffhangers
├── timeline_events
├── foreshadowing_planted: List[str]         # 新增
├── foreshadowing_paid_off: List[str]        # 新增
└── sensory_dimensions: List[str]            # 新增

ConsistencyReport
├── chapter_id, passed: bool
└── issues: List[ConsistencyIssue]
    └── issue_type, severity, description, suggestion

RiskReport
├── chapter_id
├── tension_score, villain_iq, protagonist_difficulty, arc_match
├── reader_proxy: ReaderProxyReport          # 新增
│   ├── info_overload: bool
│   ├── suspense_drive: int (1-10)
│   ├── protagonist_sentiment: str
│   └── confusion_points: List[str]
├── rhythm_check: RhythmReport               # 新增
│   ├── recent_tensions: List[int]
│   ├── trend: str (rising/falling/flat/volatile)
│   └── suggestion: str
├── rewrite_required: bool
└── suggestions: List[str]

DebateResult
├── topic, rounds: int
├── transcript: List[Speech]
├── outcome: str
└── character_changes: List[Dict]
```

## 11. RAG 知识库（可选模块）

### 11.1 数据流

```
原始文本 → DataLoader（编码检测 + 预处理）
  → TextChunker（按体裁分块）
  → EmbeddingService（BAAI/bge-m3, 1024维）
  → ChromaDB（持久化向量库）
```

### 11.2 通用化

- 当前 TextChunker 针对古典中文优化（按卷/年/条目分块）
- 通用化后支持：通用文本分块（按段落/句子）、多语言、自定义分块策略
- `rag_enabled: false` 时所有 Agent 正常工作

## 12. 持久化与存储

### 12.1 目录结构

```
data/novels/{novel_id}/
├── novel_state.json          # 项目状态（5 状态之一）
├── genre_config.yaml         # 题材配置
├── world_setting.json        # WorldSetting
├── outline/
│   └── outline.json          # Outline（含 foreshadowing_plan, rhythm_curve）
├── characters/
│   └── {character_id}.json   # Character（含 CharacterVoice）
├── chapters/
│   ├── {chapter_id}.md       # 章节正文
│   └── {chapter_id}.meta.json # 元数据（token用量、生成时间、tension_score）
├── summaries/
│   └── {chapter_id}.json     # ChapterSummary
├── director_plans/
│   └── {chapter_id}.json     # ChapterPlan（Director 输出，可追溯）
├── memory.sqlite             # 长期记忆（含伏笔、节奏、线程表）
└── exports/
    └── {novel_id}.{format}
```

### 12.2 NovelStorage 接口

```python
class NovelStorage:
    # 基础 CRUD
    save_state / load_state
    save_world_setting / load_world_setting
    save_outline / load_outline
    save_chapter / load_chapter
    save_character / load_character
    save_summary / load_summary
    # 新增
    save_director_plan / load_director_plan
    list_chapters() -> List[str]
    export(format: str)              # txt / epub / pdf
```

### 12.3 JSON 解析容错

LLM 输出 JSON 经常不规范，解析链：
1. 直接 `json.loads()`
2. 提取 ` ```json ... ``` ` 代码块
3. 正则提取最外层 `{...}` 或 `[...]`
4. 全部失败 → 返回错误，触发重试

## 13. LLM 客户端

### 13.1 ModelRegistry（配置驱动）

```yaml
models:
  kimi-k2.5:
    provider: "openai_compatible"
    endpoint: "https://ark.cn-beijing.volces.com/api/v3"
    model_id: "ep-xxx"
    api_key_env: "ARK_API_KEY"
  deepseek-chat:
    provider: "openai_compatible"
    endpoint: "https://api.deepseek.com"
    model_id: "deepseek-chat"
    api_key_env: "DEEPSEEK_API_KEY"
```

### 13.2 Agent-Model 映射

```yaml
agents:
  director:
    model: "deepseek-chat"      # 中等模型即可
    max_tokens: 4096
  writer:
    model: "kimi-k2.5"
    max_tokens: 8192            # 从 3072 提升
  context_assembler:
    model: "deepseek-chat"      # 压缩用便宜模型
    max_tokens: 2048
  # ...
```

### 13.3 多模型协作（高级，可选）

某些场景多模型协作：模型 A 生成骨架 → 模型 B 填充对话 → 模型 C 润色情感。作为可选的 `MultiModelStrategy` 配置。

## 14. 题材配置（GenreConfig）

```yaml
genre:
  type: "historical"           # historical | fantasy | urban | scifi | mystery | custom
  era: "北魏末年"               # 仅 historical
  setting_template: "historical_chinese"
  rag_enabled: true
  rag_sources: ["资治通鉴"]
  debate_enabled: true
  consistency_rules: ["timeline", "character", "geography", "history_accuracy", "foreshadowing"]
  style_guide: "半文半白"
  word_count_range: [3000, 5000]
  risk_thresholds:
    tension_min: 3
    villain_iq_min: 5
    protagonist_difficulty_min: 4
    arc_match_min: 6
    info_overload_max_new_characters: 3
```

### 14.1 Prompt 模板体系

```
config/prompts/
├── templates/
│   ├── base/                # 所有题材共享
│   ├── historical/          # 历史小说
│   ├── fantasy/             # 玄幻
│   └── ...
└── overrides/               # 项目级覆盖
    └── {novel_id}/
```

模板支持变量替换：`{{era}}`、`{{style_guide}}`、`{{genre_rules}}` 等。

## 15. 项目结构

```
src/
├── core/                    # 框架层（题材无关）
│   ├── agent.py             # BaseAgent + AgentInput/Output
│   ├── pipeline.py          # Pipeline + Stage 抽象
│   ├── middleware.py         # retry, timeout, token_tracking
│   ├── director.py          # Director Agent
│   ├── context.py           # ContextAssembler（智能压缩）
│   ├── memory/
│   │   ├── manager.py       # MemoryManager
│   │   ├── short_term.py
│   │   ├── long_term.py     # 含伏笔、节奏、线程表
│   │   └── summarizer.py
│   ├── storage.py           # NovelStorage
│   └── llm_client.py        # ModelRegistry
├── agents/                  # 7 个执行 Agent
│   ├── world_builder.py
│   ├── plot_designer.py
│   ├── writer.py
│   ├── sandbox_debater.py
│   ├── consistency_checker.py
│   ├── style_polisher.py
│   └── emotion_risk_control.py
├── knowledge/               # RAG（可选）
│   ├── rag_retriever.py
│   ├── embedding_service.py
│   ├── text_chunker.py
│   └── data_loader.py
├── genres/                  # 题材插件
│   ├── base.py              # GenrePlugin 接口
│   ├── historical.py
│   ├── fantasy.py
│   └── ...
├── cli.py                   # CLI 入口（Director 交互界面）
└── skills.py                # Claude Skills 适配层
```

核心变化：
- `core/` 和 `agents/` 分离 — 框架 vs 业务
- `genres/` 插件化 — 题材差异收敛到一个插件
- 根目录脚本全部干掉，统一走 `cli.py` 或 `skills.py`

## 16. 约束与规范

### 16.1 代码规范
- 所有 Agent 继承 `BaseAgent`，通过 `process()` 交互
- 所有 LLM 调用走 `ModelRegistry`，禁止直接构造 API 请求
- 全异步（`async/await`），禁止阻塞调用
- 循环导入防护：`from __future__ import annotations` + `TYPE_CHECKING`
- Pydantic v2，`ConfigDict(from_attributes=True)`

### 16.2 生成内容规范
- 禁止 AI 指纹：破折号滥用、解释性填充句、"总之/综上"等总结词
- 禁止现代网络用语进入古代/异世界设定
- 反派不降智，主角不无敌
- 每章至少一个转折点，结尾留钩子
- 对话要有潜台词，避免直白表达
- 对话要有"不完美感"：打断、答非所问、沉默、信息不对称
- 感官描写至少覆盖 3 种维度

### 16.3 质量闭环
- 每章必须经过 Pipeline：Writer → ConsistencyChecker → StylePolisher → EmotionRiskControl
- ConsistencyChecker 发现 error 级问题 → 回退 Writer 重写
- EmotionRiskControl 触发 rewrite_required → 回退 Writer 重写
- 自动模式下质检仍然执行，只是跳过人工 review
- Director 的 QA 重点指导每个质检 Agent 的关注方向

## 17. 通用化改造要点

从当前代码到目标系统的核心改动：

| 改动项 | 当前状态 | 目标状态 |
|--------|---------|---------|
| 编排层 | 无智能 Orchestrator | Director Agent（LLM 驱动） |
| 流水线 | 单体 Orchestrator | 可组合 Pipeline + Stage |
| 状态机 | 13 状态 | 5 状态 + Pipeline 内部管理 |
| Writer 输入 | 10 组件拼接 | WritingBrief（智能压缩） |
| 伏笔 | 无 | ForeshadowingLedger |
| 角色声音 | 无 | CharacterVoice |
| 节奏 | 单章评估 | RhythmTracker（全局序列） |
| 多线叙事 | 无 | StoryThreads |
| 信息不对称 | 无 | Director 推理生成 |
| 读者视角 | 无 | EmotionRiskControl 扩展 |
| 感官维度 | 无 | StylePolisher 检查 |
| Prompt | 硬编码北魏 | 模板化 + 变量替换 |
| 项目结构 | 扁平 | core/ + agents/ + genres/ 分层 |
| 根目录脚本 | 散落 | 统一 CLI / Skills |
| max_tokens | Writer 3072 | Writer 8192+ |
| 横切关注点 | 各 Agent 自己写 | Middleware 机制 |
| 记忆更新 | 同步阻塞 | 异步后台 |
