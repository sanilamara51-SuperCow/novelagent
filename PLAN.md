# 北魏历史小说智能体系统 - 完整实现方案

## 一、系统概览

### 核心目标
搭建一个能独立创作北魏历史小说的多智能体系统，支持穿越和架空两种模式，具备史料知识库、沙盒辩论、质量风控等高级功能。

### 技术栈
- **语言**: Python 3.11+
- **编排**: 自研状态机 + asyncio 异步调度
- **LLM 层**: LiteLLM 统一调用（支持 Claude/OpenAI/DeepSeek/Kimi/MiniMax 混用）
- **向量库**: ChromaDB
- **Embedding**: BAAI/bge-m3
- **数据存储**: JSON + SQLite

### 项目目录结构

```
F:\GIT\novel\
├── config/
│   ├── settings.yaml              # 主配置
│   ├── agents.yaml                # Agent 定义和模型分配
│   └── prompts/                   # 各 agent 的 system prompt
│       ├── world_builder.txt
│       ├── plot_designer.txt
│       ├── writer.txt
│       ├── sandbox_debater.txt
│       ├── consistency_checker.txt
│       ├── style_polisher.txt
│       └── emotion_risk_control.txt
├── src/
│   ├── __init__.py
│   ├── main.py                    # 入口
│   ├── orchestrator.py            # 编排核心
│   ├── state_machine.py           # 状态机
│   ├── context_assembler.py       # Context 组装器
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py          # 基类
│   │   ├── world_builder.py
│   │   ├── plot_designer.py
│   │   ├── writer.py
│   │   ├── sandbox_debater.py
│   │   ├── consistency_checker.py
│   │   ├── style_polisher.py
│   │   └── emotion_risk_control.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── short_term.py          # 短期记忆管理
│   │   ├── long_term.py           # 长期记忆管理
│   │   ├── rag_retriever.py       # RAG 检索
│   │   └── summarizer.py          # 摘要生成器
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── text_chunker.py        # 文本切分
│   │   ├── embedding_service.py   # Embedding 服务
│   │   └── data_loader.py         # 史料加载
│   ├── models/
│   │   ├── __init__.py
│   │   └── llm_client.py          # LiteLLM 封装
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── data/
│   ├── novels/                    # 小说项目存储
│   │   └── {novel_id}/
│   │       ├── novel_state.json   # 小说全局状态
│   │       ├── world_setting.json # 世界观设定
│   │       ├── characters/        # 角色卡片
│   │       ├── outline/           # 大纲
│   │       ├── chapters/          # 章节正文
│   │       └── summaries/         # 章节摘要
│   └── knowledge_base/            # 知识库
│       ├── raw/                   # 原始史料
│       └── chroma_db/             # 向量数据库
├── scripts/
│   ├── setup_kb.py                # 初始化知识库
│   └── download_sources.py        # 下载史料
├── requirements.txt
└── README.md
```

---

## 二、Agent 清单

### 1. WorldBuilder（世界观构建 Agent）

**职责**: 根据用户创意，构建完整的世界观设定

**输入**:
- 用户创意（朝代、时期、主角身份、故事类型）
- 史料知识库检索结果（该时期的重要史实）

**输出**:
- `world_setting.json`: 时代背景、政治格局、社会风貌、地理设定
- `timeline.json`: 关键历史事件时间线
- `factions.json`: 势力分布

**使用模型**: Claude 4 (opus) - 需要最强能力处理复杂历史背景

**System Prompt 核心**:
- 你是一位精通北魏史的历史学家和世界观设计师
- 根据用户创意，构建详细的历史小说世界观
- 穿越文: 严格遵循史实，标注可改变的节点和不可改变的节点
- 架空文: 在史实基础上合理推演
- 输出必须是结构化的 JSON，包含: era, political_system, social_structure, geography, key_events, notable_figures

**人机交互点**: 世界观初稿完成后，用户确认或修改

---

### 2. PlotDesigner（大纲设计 Agent）

**职责**: 设计全书大纲、分卷、分章

**输入**:
- 世界观设定
- 用户的故事核心诉求
- 史料知识库（相关时期的重大事件）

**输出**:
- `outline.json`: 全书结构
  - volumes: 卷列表
  - chapters: 章列表，每章包含: title, summary, key_scenes, involved_characters, historical_events, emotional_arc

**使用模型**: Claude 4 (opus) 或 DeepSeek-R1 - 需要强逻辑和规划能力

**System Prompt 核心**:
- 你是一位资深历史小说编辑和大纲设计师
- 设计符合历史小说节奏的大纲: 开局→发展→高潮→结局
- 每章必须包含明确的情绪弧线 (emotional_arc)
- 关键剧情节点需标注是否使用沙盒辩论
- 穿越文: 标注与历史事件的互动点

**人机交互点**:
- 全书大纲确认
- 分卷大纲确认
- 每章细纲（可选，批量或逐章）

---

### 3. Writer（主笔 Agent）

**职责**: 根据大纲逐章生成小说正文

**输入**:
- 当前章大纲
- 世界观摘要
- 角色状态（当前情绪、目标、关系）
- 前几章摘要（滚动窗口）
- 前一章结尾段落（保持衔接）
- RAG 检索结果（相关史料）
- 沙盒辩论结果（如本章涉及辩论场景）

**输出**:
- 章节正文（Markdown 格式）
- 写作元数据: 字数、场景列表、出场角色、时间线

**使用模型**: Claude 4 (opus) 主写 + Kimi/MiniMax 辅助场景扩展

**System Prompt 核心**:
- 你是一位擅长历史小说的专业作家
- **强制要求画面感**: 每个场景必须包含光影、色彩、微表情、动作细节
- **对话要有潜台词**: 表面说的 vs 实际想的
- **控制节奏**: 紧张场景短句、内心独白长句
- 穿越文: 主角的"现代思维"要自然流露
- 每章结尾必须留下钩子

**Context 组装策略** (详见第五节)

---

### 4. SandboxDebater（沙盒辩论 Agent）

**职责**: 处理朝堂辩论、群臣议事、多方博弈等高复杂度场景

**输入**:
- 场景设定（时间、地点、参与人物、议题）
- 各人物的立场和利益诉求
- 世界观中的势力分布

**输出**:
- 多轮对话记录（每人多轮发言）
- 辩论结果（共识/分歧/胜负）
- 各人物的情绪变化和立场微调

**使用模型**:
- 每个 NPC 用一个独立的 LLM 调用（可并行）
- NPC 用轻量级模型（Kimi/MiniMax）
- 主持人/观察员用 Claude 4

**System Prompt 核心（NPC 模板）**:
- 你扮演 {人物姓名}，{身份}，{性格特征}
- 你的核心利益是: {利益诉求}
- 你对 {其他人物} 的态度是: {态度}
- 在当前议题上，你的立场是: {立场}
- 请用符合你身份和性格的口吻发言，考虑政治后果

**工作流程**:
1. 初始化: 为每个 NPC 生成角色卡
2. 多轮辩论: 每轮每个 NPC 根据上轮发言生成回应
3. 终止条件: 达成共识 / 达到最大轮数 / 主持人判定可以结束
4. 输出: 整理为时间线式的对话记录

**人机交互点**: 辩论方向关键抉择（可选让用户干预）

---

### 5. ConsistencyChecker（一致性审查 Agent）

**职责**: 检查时间线、人物、事件一致性

**输入**:
- 新写的章节
- 已确认的历史事件时间线
- 角色卡片（当前状态 vs 新章节中的状态）
- 前几章摘要

**输出**:
- 一致性报告: issues[]
  - 类型: timeline / character / geography / history
  - 严重程度: error / warning
  - 描述
  - 建议修改

**使用模型**: DeepSeek-R1 或 Claude 4 - 需要细致和逻辑能力

**System Prompt 核心**:
- 你是一位严谨的历史小说编辑
- 逐句检查新章节与已有设定的一致性
- 检查项:
  - 时间线: 事件顺序是否正确
  - 人物: 称谓、官职、性格是否一致
  - 地理: 地点间移动时间是否合理
  - 史实: 是否违背已确认的史实（穿越文）
- 输出结构化的审查报告

---

### 6. StylePolisher（风格润色 Agent）

**职责**: 统一文风、优化节奏、增强画面感

**输入**:
- 初稿章节
- 目标文风设定（半文半白/纯白话/古风）

**输出**:
- 润色后的章节
- 修改说明

**使用模型**: Claude 4 或 Kimi - 需要语言美感

**System Prompt 核心**:
- 你是一位资深文学编辑
- 润色目标:
  - 统一文风，保持半文半白的质感
  - 优化句式节奏，长短句交错
  - 增强画面感和氛围营造
  - 精简冗余描写，强化关键细节
- 保留原文的核心情节和对话内容

---

### 7. EmotionRiskControl（情绪风控 Agent）

**职责**: 审核章节张力，防止"爽文化"和平庸推进

**输入**:
- 润色后的章节
- 该章大纲的预期情绪弧线

**输出**:
- 风险评估报告:
  - tension_score: 1-10 (张力分数)
  - villain_iq: 1-10 (反派智商)
  - protagonist_difficulty: 1-10 (主角难度)
  - issues: 问题列表
  - rewrite_required: bool
  - suggestions: 改进建议

**使用模型**: Claude 4 - 需要判断力和文学素养

**System Prompt 核心**:
- 你是一位苛刻的历史小说编辑，专精权谋文
- 审核标准:
  - 主角是否赢得太轻松？胜利必须有代价
  - 反派是否降智？反派必须有自己的逻辑
  - 是否有"生死一线"的压迫感？
  - 破局方式是否惊艳？避免俗套
  - 情绪弧线是否符合大纲设计？
- 如果不达标，明确打回重写，并给出具体改进方向

**人机交互点**: 风控未通过时，用户决定是否接受建议重写

---

## 三、编排流程（完整工作流）

### Phase 0: 初始化
```
1. 用户输入: 创意（朝代/时期/主角身份/故事类型）
2. WorldBuilder
   └─→ 检索知识库（该时期史料）
   └─→ 生成世界观设定
3. 用户确认/修改世界观
4. 保存: world_setting.json, timeline.json, factions.json
```

### Phase 1: 大纲设计
```
5. PlotDesigner
   └─→ 读取世界观
   └─→ 检索知识库（相关历史事件）
   └─→ 生成全书大纲
6. 用户确认全书大纲
7. PlotDesigner
   └─→ 生成分卷大纲
8. 用户确认分卷大纲（可选逐章）
9. 保存: outline.json
```

### Phase 2: 章节写作循环
```
对于每一章:

    10. 检查本章是否需要沙盒辩论
        ├─→ 是: 进入 SandboxDebater 流程
        │       ├─→ 初始化 NPC
        │       ├─→ 多轮辩论
        │       └─→ 输出辩论记录
        └─→ 否: 跳过

    11. Writer
        ├─→ 组装 Context
        ├─→ 生成初稿
        └─→ 保存初稿

    12. ConsistencyChecker
        ├─→ 检查一致性
        └─→ 如果不通过:
            ├─→ Writer 修改
            └─→ 重新检查

    13. StylePolisher
        ├─→ 润色
        └─→ 保存润色稿

    14. EmotionRiskControl
        ├─→ 风险评估
        └─→ 如果不通过:
            ├─→ 用户确认: 是否重写?
            ├─→ 是: Writer 重写（带改进建议）
            └─→ 否: 保留，标记风险

    15. 生成章节摘要
        └─→ Summarizer 提取关键信息

    16. 更新长期记忆
        ├─→ 更新角色状态
        ├─→ 更新事件记录
        └─→ 保存摘要到 summaries/

    17. 用户确认/反馈
        └─→ 可选: 局部修改指令

    18. 保存最终章节到 chapters/{chapter_id}.md
```

### Phase 3: 完成
```
19. 生成小说元数据
20. 导出完整小说（合并所有章节）
```

---

## 四、状态管理

### NovelState 数据结构

```python
@dataclass
class NovelState:
    """小说全局状态"""
    novel_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    # 基本设定
    setting: WorldSetting  # 世界观设定
    story_type: Literal["time_travel", "alternate_history"]  # 穿越/架空

    # 大纲
    outline: Outline  # 完整大纲
    current_volume: int  # 当前卷
    current_chapter: int  # 当前章

    # 进度状态
    phase: Literal["init", "outline", "writing", "completed"]
    status: Literal["idle", "running", "waiting_user", "error"]

    # 历史记录
    completed_chapters: List[str]  # 已完成章节ID列表
    pending_decisions: List[Decision]  # 待用户决策

@dataclass
class WorldSetting:
    """世界观设定"""
    era: str  # 时期，如 "太和年间"
    year_range: Tuple[int, int]  # 公元年份范围
    political_system: str  # 政治制度
    social_structure: str  # 社会结构
    geography: Dict[str, Any]  # 地理设定
    key_events: List[HistoricalEvent]  # 关键历史事件
    factions: List[Faction]  # 势力分布
    notable_figures: List[Figure]  # 重要人物

@dataclass
class Outline:
    """大纲结构"""
    volumes: List[Volume]
    total_chapters: int
    core_conflict: str  # 核心冲突
    protagonist_arc: str  # 主角成长弧线

@dataclass
class Volume:
    """卷"""
    volume_number: int
    title: str
    summary: str
    chapters: List[ChapterOutline]
    emotional_theme: str  # 本卷情绪主题

@dataclass
class ChapterOutline:
    """章大纲"""
    chapter_id: str
    chapter_number: int
    title: str
    summary: str
    key_scenes: List[Scene]  # 关键场景
    involved_characters: List[str]  # 涉及角色
    historical_events: List[str]  # 涉及历史事件
    emotional_arc: EmotionalArc  # 情绪弧线
    requires_debate: bool  # 是否需要沙盒辩论
    debate_config: Optional[DebateConfig]  # 辩论配置

@dataclass
class Character:
    """角色卡片"""
    character_id: str
    name: str
    aliases: List[str]  # 别名、字号
    identity: str  # 身份
    personality: str  # 性格
    background: str  # 背景
    goals: List[str]  # 目标
    relationships: Dict[str, str]  # 与其他角色的关系
    current_status: CharacterStatus  # 当前状态
    history: List[CharacterEvent]  # 经历时间线

@dataclass
class CharacterStatus:
    """角色当前状态（每章更新）"""
    chapter_id: str  # 最后更新章节
    location: str  # 当前位置
    position: str  # 当前职位
    health: str  # 健康状况
    mood: str  # 情绪状态
    key_info: List[str]  # 当前掌握的关键信息
```

---

## 五、Context 组装策略

这是系统的核心，决定每次调用 LLM 时如何组织信息。

### 5.1 通用 Context 结构

```python
class ContextAssembler:
    def assemble(self, agent_type: str, task: Task) -> List[Dict]:
        messages = []

        # 1. System Prompt
        system_prompt = self.load_system_prompt(agent_type)
        messages.append({"role": "system", "content": system_prompt})

        # 2. 世界观摘要（动态压缩）
        world_summary = self.get_world_summary()
        messages.append({"role": "user", "content": f"【世界观摘要】\n{world_summary}"})

        # 3. 当前情境
        if task.chapter_id:
            context = self.get_chapter_context(task.chapter_id)
            messages.append({"role": "user", "content": f"【当前情境】\n{context}"})

        # 4. 角色状态
        if task.involved_characters:
            char_status = self.get_characters_status(task.involved_characters)
            messages.append({"role": "user", "content": f"【角色状态】\n{char_status}"})

        # 5. RAG 检索结果
        if task.query:
            rag_results = self.rag_retrieve(task.query)
            messages.append({"role": "user", "content": f"【史料参考】\n{rag_results}"})

        # 6. 具体任务指令
        messages.append({"role": "user", "content": f"【任务】\n{task.instruction}"})

        return messages
```

### 5.2 各 Agent 的 Context 定制

#### Writer 的特殊 Context

```python
def assemble_writer_context(self, chapter_outline: ChapterOutline) -> List[Dict]:
    messages = []

    # System Prompt
    messages.append({"role": "system", "content": WRITER_PROMPT})

    # 世界观（精简版，< 1000 tokens）
    world_brief = self.summarize_world(self.novel_state.setting, max_tokens=1000)
    messages.append({"role": "user", "content": f"故事背景:\n{world_brief}"})

    # 本章大纲
    messages.append({"role": "user", "content": f"本章要求:\n{chapter_outline.summary}"})
    messages.append({"role": "user", "content": f"情绪弧线: {chapter_outline.emotional_arc}"})

    # 关键场景
    for scene in chapter_outline.key_scenes:
        messages.append({"role": "user", "content": f"场景: {scene.description}"})

    # 角色状态（涉及角色）
    for char_id in chapter_outline.involved_characters:
        char = self.get_character(char_id)
        char_brief = f"{char.name}: {char.current_status.position}, {char.current_status.mood}"
        messages.append({"role": "user", "content": f"角色状态: {char_brief}"})

    # 前文摘要（滚动窗口，最近 3 章）
    recent_summaries = self.get_recent_summaries(n=3)
    messages.append({"role": "user", "content": f"前情提要:\n{recent_summaries}"})

    # 前一章结尾（保持衔接）
    if self.current_chapter > 1:
        last_ending = self.get_chapter_ending(self.current_chapter - 1)
        messages.append({"role": "user", "content": f"上一章结尾:\n{last_ending}"})

    # 史料参考（RAG 检索）
    if chapter_outline.historical_events:
        for event in chapter_outline.historical_events:
            docs = self.rag.search(event, n_results=3)
            messages.append({"role": "user", "content": f"相关史料({event}):\n{docs}"})

    # 沙盒辩论结果（如果有）
    if chapter_outline.requires_debate:
        debate_result = self.get_debate_result(chapter_outline.chapter_id)
        messages.append({"role": "user", "content": f"朝堂辩论记录:\n{debate_result}"})

    # 写作指令
    messages.append({"role": "user", "content": WRITE_INSTRUCTION})

    return messages
```

#### SandboxDebater 的 Context

```python
def assemble_npc_context(self, npc_id: str, debate_round: int,
                         previous_speeches: List[Speech]) -> List[Dict]:
    npc = self.get_character(npc_id)

    messages = []

    # NPC 角色卡
    system_prompt = f"""你是 {npc.name}，{npc.identity}。
性格: {npc.personality}
核心利益: {npc.goals}
当前情绪: {npc.current_status.mood}
与其他人的关系: {npc.relationships}

你在一场朝堂辩论中，必须基于你的身份、利益和性格发言。
考虑政治后果，你的话会影响你的前途甚至生死。"""

    messages.append({"role": "system", "content": system_prompt})

    # 辩论背景
    messages.append({"role": "user", "content": f"辩论议题: {self.current_debate.topic}"})
    messages.append({"role": "user", "content": f"你的立场: {self.current_debate.get_stance(npc_id)}"})

    # 前几轮发言
    for speech in previous_speeches:
        role = "assistant" if speech.speaker_id == npc_id else "user"
        content = f"{speech.speaker_name}: {speech.content}"
        messages.append({"role": role, "content": content})

    # 本轮发言指令
    messages.append({"role": "user", "content": "现在轮到你发言。考虑前面的发言，做出你的回应。"})

    return messages
```

---

## 六、记忆系统

### 6.1 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                     三层记忆架构                             │
├─────────────┬─────────────┬─────────────────────────────────┤
│  短期记忆    │  长期记忆    │      外部记忆 (RAG)             │
├─────────────┼─────────────┼─────────────────────────────────┤
│ • 当前章节   │ • 角色卡片   │ • 史料知识库                   │
│   上下文     │ • 事件摘要   │   (《魏书》《资治通鉴》等)      │
│ • 前3章摘要 │ • 世界设定   │ • 已写章节全文检索              │
│ • 当前任务   │ • 人物关系图 │                                 │
│   参数      │ • 时间线     │                                 │
├─────────────┼─────────────┼─────────────────────────────────┤
│ Context中   │ JSON文件    │ ChromaDB向量库                   │
│ 显式携带    │ + SQLite    │ + 原始文本                       │
├─────────────┼─────────────┼─────────────────────────────────┤
│ ~4K tokens │ 无限制      │ GB级别                          │
└─────────────┴─────────────┴─────────────────────────────────┘
```

### 6.2 记忆更新流程

每章写完后:

```python
async def update_memory_after_chapter(self, chapter: Chapter):
    # 1. 生成章节摘要
    summary = await self.summarizer.summarize(chapter)
    # 摘要包含: 核心事件、角色变化、关键对话、情绪转折

    # 2. 更新角色状态
    for char_change in summary.character_changes:
        char = self.get_character(char_change.character_id)
        char.current_status.update(char_change.new_status)
        char.history.append(CharacterEvent(
            chapter_id=chapter.id,
            event=char_change.description
        ))

    # 3. 更新世界时间线
    for event in summary.events:
        self.novel_state.setting.timeline.mark_event(
            event.time, event.description, chapter.id
        )

    # 4. 保存摘要到长期记忆
    self.memory.save_summary(summary)

    # 5. 索引章节内容到 RAG（可选，用于后续检索）
    self.rag.index_document(
        doc_id=f"chapter_{chapter.id}",
        content=chapter.content,
        metadata={
            "chapter_id": chapter.id,
            "title": chapter.title,
            "characters": chapter.involved_characters
        }
    )
```

### 6.3 摘要生成器

```python
class Summarizer:
    """用 LLM 生成章节摘要"""

    async def summarize(self, chapter: Chapter) -> ChapterSummary:
        prompt = f"""
        请对以下小说章节生成结构化摘要:

        章节标题: {chapter.title}
        章节内容:
        {chapter.content}

        请提取:
        1. 核心事件 (3-5条)
        2. 角色变化 (每个出场角色的状态变化)
        3. 关键对话/决策
        4. 情绪转折点
        5. 留下的悬念

        输出为 JSON 格式。
        """

        response = await self.llm.generate(prompt)
        return ChapterSummary.parse(response)
```

---

## 七、模型分配策略

### 7.1 各 Agent 模型选择

| Agent | 推荐模型 | 备选模型 | 理由 |
|-------|---------|---------|------|
| WorldBuilder | Claude 4 (opus) | DeepSeek-R1 | 需最强创意和知识整合 |
| PlotDesigner | Claude 4 (opus) | DeepSeek-R1 | 长程规划，逻辑严密 |
| Writer | Claude 4 (opus) | Kimi k1.5 | 核心创作，质量优先 |
| SandboxDebater (NPC) | Kimi/MiniMax | DeepSeek-V3 | 并发多实例，成本控制 |
| SandboxDebater (主持) | Claude 4 | - | 整合辩论结果 |
| ConsistencyChecker | DeepSeek-R1 | Claude 4 | 逻辑检查，细致 |
| StylePolisher | Claude 4 | Kimi | 语言美感 |
| EmotionRiskControl | Claude 4 | - | 判断力要求高 |
| Summarizer | Kimi | MiniMax | 便宜够用 |

### 7.2 成本优化策略

```python
class ModelRouter:
    """根据任务复杂度路由到不同模型"""

    def route(self, task: Task) -> str:
        # 简单任务用便宜模型
        if task.type == "summarize":
            return "kimi"

        # 需要创造力的用 Claude
        if task.type in ["write", "world_build", "plot_design"]:
            return "claude-opus-4-6"

        # 逻辑任务用 R1 或 Claude
        if task.type in ["check", "debate_host"]:
            return "deepseek-r1"  # 或 claude-opus

        # NPC 辩论并行用便宜模型
        if task.type == "npc_speak":
            return "kimi"  # 或 minimax
```

---

## 八、人机交互设计

### 8.1 交互点清单

| 阶段 | 交互点 | 交互方式 |
|------|-------|---------|
| 初始化 | 世界观确认 | 展示 world_setting.json，用户可编辑 |
| 大纲 | 全书大纲确认 | 展示 outline.md，用户可调整卷章结构 |
| 大纲 | 分卷大纲确认 | 逐卷确认或批量确认 |
| 写作 | 沙盒辩论方向 | 辩论关键抉择点询问用户 |
| 写作 | 风控未通过 | 展示问题和建议，用户决定是否重写 |
| 写作 | 章节完成 | 展示章节，用户可提出修改意见 |
| 全局 | 角色命运 | 关键角色死亡/重大转变前询问用户 |

### 8.2 CLI 交互界面

```python
# 简化的命令行交互示例
class NovelCLI:
    async def review_world_setting(self):
        print("=== 世界观设定 ===")
        print(json.dumps(self.world_setting, indent=2, ensure_ascii=False))

        choice = input("\n[确认/编辑/重新生成] (c/e/r): ")
        if choice == "e":
            # 打开编辑器让用户修改 JSON
            edited = self.open_editor(self.world_setting)
            self.world_setting = edited
        elif choice == "r":
            await self.regenerate_world_setting()

    async def review_chapter(self, chapter: Chapter):
        print(f"=== {chapter.title} ===")
        print(chapter.content[:2000] + "...")  # 预览

        choice = input("\n[通过/修改/重写/退出] (p/m/r/q): ")
        if choice == "m":
            instruction = input("请输入修改意见: ")
            await self.writer.revise(chapter, instruction)
```

---

## 九、史料知识库搭建

### 9.1 数据来源优先级

1. **GitHub 现成语料** (最优先)
   - 搜索关键词: `二十四史 txt`, `chinese-history-corpus`
   - 如找到可直接使用

2. **维基文库 API** (推荐)
   - 《魏书》124卷完整
   - 《资治通鉴》全文
   - 《洛阳伽蓝记》
   - 使用 MediaWiki API 获取

3. **ctext.org API** (补充)
   - 《水经注》
   - 部分《魏书》
   - 需要注册账号

### 9.2 数据加载流程

```python
# scripts/setup_kb.py

async def setup_knowledge_base():
    # 1. 下载/加载原始文本
    sources = [
        ("weishu", "维基文库", "魏書"),
        ("zizhitongjian", "维基文库", "資治通鑑"),
        ("luoyang", "维基文库", "洛陽伽藍記"),
    ]

    for source_id, platform, title in sources:
        raw_text = await download_source(platform, title)

        # 2. 清洗和切分
        chunks = chunk_text(source_id, raw_text)

        # 3. 生成元数据
        for chunk in chunks:
            chunk.metadata = generate_metadata(chunk)

        # 4. Embedding 和入库
        await index_to_chroma(chunks)

def chunk_text(source_id: str, text: str) -> List[Chunk]:
    """按文本类型使用不同切分策略"""

    if source_id == "weishu":
        # 纪传体: 按传切分
        return chunk_by_biography(text)

    elif source_id == "zizhitongjian":
        # 编年体: 按年切分
        return chunk_by_year(text)

    elif source_id == "luoyang":
        # 地理志: 按寺院/条目切分
        return chunk_by_entry(text)
```

### 9.3 切分策略详解

```python
# src/knowledge/text_chunker.py

class TextChunker:
    def chunk_weishu(self, text: str) -> List[Chunk]:
        """《魏书》切分: 按列传为单位"""
        chunks = []

        # 匹配 "卷XX·列传第XX·XXX传" 模式
        pattern = r'卷[一二三四五六七八九十百千]+·列傳第[一二三四五六七八九十百千]+·([^·]+傳)'
        sections = re.split(pattern, text)

        for i in range(1, len(sections), 2):
            title = sections[i]
            content = sections[i+1]

            # 长传再按段落切
            if len(content) > 1000:
                sub_chunks = self.split_long_biography(title, content)
                chunks.extend(sub_chunks)
            else:
                chunks.append(Chunk(
                    title=title,
                    content=content,
                    metadata={
                        "source": "魏书",
                        "type": "biography",
                        "person": title.replace("傳", ""),
                    }
                ))

        return chunks

    def chunk_zizhitongjian(self, text: str) -> List[Chunk]:
        """《资治通鉴》切分: 按年为单位"""
        chunks = []

        # 匹配 "XX年" 或 "XX元年" 等年号
        pattern = r'([太延|太平真君|正平|文成帝|獻文帝|孝文帝延興|承明|太和|宣武帝景明|正始|永平|延昌|孝明帝熙平|神龜|正光|孝莊帝建義|永安|節閔帝普泰|廢帝中興|孝武帝太昌|永興|永熙]+[元一二三四五六七八九十百千]+年)'

        sections = re.split(pattern, text)

        for i in range(1, len(sections), 2):
            year = sections[i]
            content = sections[i+1]

            # 提取涉及人物
            persons = self.extract_persons(content)

            chunks.append(Chunk(
                title=year,
                content=content[:2000],  # 控制长度
                metadata={
                    "source": "资治通鉴",
                    "type": "annals",
                    "year": year,
                    "persons": persons,
                }
            ))

        return chunks
```

---

## 十、配置文件设计

### 10.1 settings.yaml

```yaml
# 项目配置
project:
  name: "北魏历史小说智能体"
  data_dir: "./data"
  log_level: "INFO"

# LLM 配置
llm:
  default_model: "claude-opus-4-6"

  # 各模型 API 配置 (LiteLLM 格式)
  models:
    claude-opus-4-6:
      model: "anthropic/claude-opus-4-6"
      api_key: "${CLAUDE_API_KEY}"
      max_tokens: 4096
      temperature: 0.7

    gpt-4o:
      model: "openai/gpt-4o"
      api_key: "${OPENAI_API_KEY}"
      max_tokens: 4096
      temperature: 0.7

    deepseek-r1:
      model: "deepseek/deepseek-reasoner"
      api_key: "${DEEPSEEK_API_KEY}"
      max_tokens: 4096
      temperature: 0.7

    kimi:
      model: "openrouter/moonshotai/kimi-k2"
      api_key: "${OPENROUTER_API_KEY}"
      max_tokens: 4096
      temperature: 0.7

    minimax:
      model: "openrouter/minimax/minimax-01"
      api_key: "${OPENROUTER_API_KEY}"
      max_tokens: 4096
      temperature: 0.7

# Agent 模型分配
agents:
  world_builder:
    model: "claude-opus-4-6"
    max_tokens: 4096

  plot_designer:
    model: "claude-opus-4-6"
    max_tokens: 4096

  writer:
    model: "claude-opus-4-6"
    max_tokens: 8192  # 写作需要更长输出

  sandbox_debater:
    npc_model: "kimi"  # NPC 用便宜模型
    host_model: "claude-opus-4-6"
    max_rounds: 5
    npc_concurrent: true

  consistency_checker:
    model: "deepseek-r1"
    max_tokens: 4096

  style_polisher:
    model: "claude-opus-4-6"
    max_tokens: 8192

  emotion_risk_control:
    model: "claude-opus-4-6"
    max_tokens: 4096

  summarizer:
    model: "kimi"
    max_tokens: 2048

# RAG 配置
rag:
  embedding_model: "BAAI/bge-m3"
  vector_db_path: "./data/knowledge_base/chroma_db"
  chunk_size: 800
  chunk_overlap: 150
  top_k: 5

# 记忆系统配置
memory:
  short_term_window: 3  # 前几章摘要
  summary_max_tokens: 500

# 工作流配置
workflow:
  auto_mode: false  # 是否自动运行（无需用户确认）
  review_points:  # 需要用户确认的环节
    - world_setting
    - outline
    - emotion_risk_fail
```

### 10.2 agents.yaml

```yaml
# Agent 详细定义
agents:
  world_builder:
    name: "WorldBuilder"
    description: "构建小说世界观"
    system_prompt: "prompts/world_builder.txt"
    output_schema: "schemas/world_setting.json"

  plot_designer:
    name: "PlotDesigner"
    description: "设计小说大纲"
    system_prompt: "prompts/plot_designer.txt"
    output_schema: "schemas/outline.json"

  writer:
    name: "Writer"
    description: "创作小说章节"
    system_prompt: "prompts/writer.txt"
    context_assembler: "writer"  # 使用专门的 context 组装器

  sandbox_debater:
    name: "SandboxDebater"
    description: "沙盒辩论室"
    npc_prompt: "prompts/npc.txt"
    host_prompt: "prompts/debate_host.txt"

  consistency_checker:
    name: "ConsistencyChecker"
    description: "一致性审查"
    system_prompt: "prompts/consistency_checker.txt"
    output_schema: "schemas/consistency_report.json"

  style_polisher:
    name: "StylePolisher"
    description: "风格润色"
    system_prompt: "prompts/style_polisher.txt"

  emotion_risk_control:
    name: "EmotionRiskControl"
    description: "情绪风控"
    system_prompt: "prompts/emotion_risk_control.txt"
    output_schema: "schemas/risk_report.json"
```

---

## 十一、关键实现细节

### 11.1 状态机设计

```python
# src/state_machine.py

from enum import Enum, auto
from typing import Dict, Callable
import asyncio

class State(Enum):
    IDLE = auto()
    INIT_WORLD = auto()
    WAIT_WORLD_CONFIRM = auto()
    DESIGN_OUTLINE = auto()
    WAIT_OUTLINE_CONFIRM = auto()
    WRITE_CHAPTER = auto()
    DEBATE = auto()
    CHECK_CONSISTENCY = auto()
    POLISH = auto()
    RISK_CONTROL = auto()
    WAIT_CHAPTER_CONFIRM = auto()
    UPDATE_MEMORY = auto()
    COMPLETED = auto()
    ERROR = auto()

class NovelStateMachine:
    def __init__(self, orchestrator):
        self.state = State.IDLE
        self.orchestrator = orchestrator
        self.transitions: Dict[State, Dict[str, tuple]] = {
            State.IDLE: {
                "start": (State.INIT_WORLD, self.orchestrator.init_world),
            },
            State.INIT_WORLD: {
                "done": (State.WAIT_WORLD_CONFIRM, self.orchestrator.present_world),
            },
            State.WAIT_WORLD_CONFIRM: {
                "confirm": (State.DESIGN_OUTLINE, self.orchestrator.design_outline),
                "edit": (State.INIT_WORLD, self.orchestrator.edit_world),
            },
            State.DESIGN_OUTLINE: {
                "done": (State.WAIT_OUTLINE_CONFIRM, self.orchestrator.present_outline),
            },
            State.WAIT_OUTLINE_CONFIRM: {
                "confirm": (State.WRITE_CHAPTER, self.orchestrator.write_chapter),
                "edit": (State.DESIGN_OUTLINE, self.orchestrator.edit_outline),
            },
            State.WRITE_CHAPTER: {
                "needs_debate": (State.DEBATE, self.orchestrator.run_debate),
                "done": (State.CHECK_CONSISTENCY, self.orchestrator.check_consistency),
            },
            State.DEBATE: {
                "done": (State.WRITE_CHAPTER, self.orchestrator.write_with_debate),
            },
            State.CHECK_CONSISTENCY: {
                "pass": (State.POLISH, self.orchestrator.polish),
                "fail": (State.WRITE_CHAPTER, self.orchestrator.revise_for_consistency),
            },
            State.POLISH: {
                "done": (State.RISK_CONTROL, self.orchestrator.risk_control),
            },
            State.RISK_CONTROL: {
                "pass": (State.WAIT_CHAPTER_CONFIRM, self.orchestrator.present_chapter),
                "fail": (State.WAIT_CHAPTER_CONFIRM, self.orchestrator.present_with_warning),
            },
            State.WAIT_CHAPTER_CONFIRM: {
                "confirm": (State.UPDATE_MEMORY, self.orchestrator.update_memory),
                "revise": (State.WRITE_CHAPTER, self.orchestrator.revise_chapter),
            },
            State.UPDATE_MEMORY: {
                "done": (State.WRITE_CHAPTER, self.orchestrator.next_chapter),
                "complete": (State.COMPLETED, self.orchestrator.finalize),
            },
        }

    async def transition(self, event: str, **kwargs):
        if self.state not in self.transitions:
            raise ValueError(f"No transitions from state {self.state}")

        if event not in self.transitions[self.state]:
            raise ValueError(f"No transition for event {event} from state {self.state}")

        next_state, action = self.transitions[self.state][event]

        # 执行动作
        result = await action(**kwargs)

        # 更新状态
        self.state = next_state

        return result
```

### 11.2 沙盒辩论实现

```python
# src/agents/sandbox_debater.py

import asyncio
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Speech:
    round: int
    speaker_id: str
    speaker_name: str
    content: str
    emotion: str  # 当前情绪

class SandboxDebater:
    def __init__(self, config, llm_client):
        self.config = config
        self.llm = llm_client
        self.max_rounds = config.max_rounds

    async def run_debate(
        self,
        topic: str,
        npcs: List[Character],
        context: Dict
    ) -> DebateResult:
        """运行多轮辩论"""

        # 初始化每轮的记录
        all_speeches: List[List[Speech]] = []

        for round_num in range(self.max_rounds):
            round_speeches = []

            # 每个 NPC 发言（并行）
            tasks = []
            for npc in npcs:
                task = self._generate_npc_speech(
                    npc=npc,
                    topic=topic,
                    round_num=round_num,
                    previous_speeches=all_speeches,
                    context=context
                )
                tasks.append(task)

            speeches = await asyncio.gather(*tasks)
            round_speeches.extend(speeches)
            all_speeches.append(round_speeches)

            # 检查是否达成共识或可以提前结束
            if self._should_end_debate(all_speeches):
                break

        # 主持人整理辩论结果
        result = await self._summarize_debate(topic, all_speeches, npcs)

        return result

    async def _generate_npc_speech(
        self,
        npc: Character,
        topic: str,
        round_num: int,
        previous_speeches: List[List[Speech]],
        context: Dict
    ) -> Speech:
        """生成单个 NPC 的发言"""

        # 组装该 NPC 的 context
        messages = self._assemble_npc_context(
            npc, topic, round_num, previous_speeches, context
        )

        # 调用轻量级模型
        response = await self.llm.generate(
            model=self.config.npc_model,
            messages=messages,
            max_tokens=500,
            temperature=0.8  # NPC 需要一定随机性
        )

        # 解析情绪和发言
        content = response.content
        emotion = self._extract_emotion(content) or npc.current_status.mood

        return Speech(
            round=round_num,
            speaker_id=npc.character_id,
            speaker_name=npc.name,
            content=content,
            emotion=emotion
        )

    def _assemble_npc_context(
        self,
        npc: Character,
        topic: str,
        round_num: int,
        previous_speeches: List[List[Speech]],
        context: Dict
    ) -> List[Dict]:
        """组装 NPC 的上下文"""

        messages = []

        # System: NPC 角色卡
        system_prompt = f"""你是 {npc.name}，{npc.identity}。

【性格特质】
{npc.personality}

【核心利益】
{chr(10).join(npc.goals)}

【与其他人的关系】
{chr(10).join([f"- {name}: {relation}" for name, relation in npc.relationships.items()])}

【当前状态】
- 职位: {npc.current_status.position}
- 情绪: {npc.current_status.mood}
- 掌握信息: {chr(10).join(npc.current_status.key_info)}

你正在参加一场朝堂辩论。请记住你的身份、利益和立场，考虑政治后果发言。"""

        messages.append({"role": "system", "content": system_prompt})

        # User: 辩论背景
        messages.append({"role": "user", "content": f"辩论议题: {topic}"})
        messages.append({"role": "user", "content": f"你对这个议题的立场是: {context.get('stances', {}).get(npc.character_id, '观望')}"})

        # 历史发言（转换格式）
        for round_speeches in previous_speeches:
            for speech in round_speeches:
                if speech.speaker_id == npc.character_id:
                    # 自己的发言作为 assistant
                    messages.append({"role": "assistant", "content": speech.content})
                else:
                    # 别人的发言作为 user，但标记说话人
                    messages.append({
                        "role": "user",
                        "content": f"[{speech.speaker_name}]: {speech.content}"
                    })

        # 本轮发言指令
        messages.append({"role": "user", "content": "现在轮到你发言。基于前面的讨论，表明你的立场和观点。注意你的措辞要符合你的身份和当前情绪。"})

        return messages

    async def _summarize_debate(
        self,
        topic: str,
        all_speeches: List[List[Speech]],
        npcs: List[Character]
    ) -> DebateResult:
        """主持人整理辩论结果"""

        # 构建辩论记录文本
        debate_text = ""
        for i, round_speeches in enumerate(all_speeches):
            debate_text += f"\n=== 第 {i+1} 轮 ===\n"
            for speech in round_speeches:
                debate_text += f"{speech.speaker_name} ({speech.emotion}): {speech.content}\n\n"

        prompt = f"""
        你是一位资深史官，正在记录一场朝堂辩论。

        议题: {topic}

        辩论记录:
        {debate_text}

        请整理辩论结果，包括:
        1. 各方核心观点摘要
        2. 辩论过程中的关键交锋
        3. 最终结果（共识/分歧/胜负）
        4. 各人物在辩论后的情绪变化和立场微调
        5. 对后续剧情的影响

        输出为结构化 JSON。
        """

        response = await self.llm.generate(
            model=self.config.host_model,
            prompt=prompt,
            max_tokens=2000
        )

        return DebateResult.parse(response.content)
```

---

## 十二、实施路线图

### Phase 1: 基础设施 (Week 1)
- [ ] 项目骨架搭建
- [ ] LiteLLM 封装
- [ ] ChromaDB 集成
- [ ] 配置系统
- [ ] 日志系统

### Phase 2: 核心 Agent (Week 2)
- [ ] BaseAgent 基类
- [ ] WorldBuilder
- [ ] PlotDesigner
- [ ] Writer (基础版)
- [ ] ContextAssembler

### Phase 3: 记忆系统 (Week 3)
- [ ] ShortTermMemory
- [ ] LongTermMemory
- [ ] Summarizer
- [ ] 记忆更新流程

### Phase 4: 知识库 (Week 3-4)
- [ ] 史料下载脚本
- [ ] TextChunker
- [ ] EmbeddingService
- [ ] RAGRetriever

### Phase 5: 高级功能 (Week 4)
- [ ] SandboxDebater
- [ ] ConsistencyChecker
- [ ] StylePolisher
- [ ] EmotionRiskControl

### Phase 6: 编排与 UI (Week 5)
- [ ] StateMachine
- [ ] Orchestrator
- [ ] CLI 界面
- [ ] 人机交互流程

### Phase 7: 测试与优化 (Week 6)
- [ ] 端到端测试
- [ ] Prompt 调优
- [ ] 成本优化
- [ ] 文档完善

---

## 十三、风险与对策

| 风险 | 影响 | 对策 |
|-----|------|-----|
| Context 过长超出限制 | 高 | 动态压缩摘要，分级加载 |
| LLM API 不稳定 | 高 | 多模型备份，失败重试 |
| 史料知识库质量差 | 中 | 人工校验关键章节，多源交叉 |
| 生成内容一致性差 | 中 | 强化 ConsistencyChecker，用户复核 |
| 成本过高 | 中 | 轻量模型处理简单任务，Claude 只用于核心创作 |
| 沙盒辩论质量不稳定 | 中 | 限制轮数，主持人强力干预 |

---

## 十四、附录：Prompt 模板

### WorldBuilder System Prompt

```
你是一位精通北魏史的历史学家和世界观设计师。你的任务是根据用户的创意，构建一个详细、可信的历史小说世界观。

## 你的能力
- 精通北魏历史（386-534年），包括政治、经济、社会、文化、军事
- 了解南北朝时期的民族关系、汉化进程、佛教传播
- 能够区分正史、野史和小说演绎

## 输出要求
输出必须是结构化的 JSON，包含以下字段：

{
  "era": "时期名称，如'太和年间'",
  "year_range": [477, 499],
  "political_system": "政治制度详细描述",
  "social_structure": "社会结构，包括鲜卑贵族、汉族士族、平民等",
  "geography": {
    "capital": "都城",
    "key_locations": ["重要地点列表"]
  },
  "key_events": [
    {
      "year": 490,
      "event": "事件名称",
      "description": "事件描述",
      "changeable": true/false
    }
  ],
  "factions": [
    {
      "name": "势力名称",
      "leader": "领袖",
      "stance": "立场",
      "strength": "实力评估"
    }
  ],
  "notable_figures": [
    {
      "name": "姓名",
      "identity": "身份",
      "personality": "性格",
      "current_position": "当前职位"
    }
  ]
}

## 特别说明
- 穿越文: 严格标注哪些历史事件可以改变，哪些不可改变
- 架空文: 在史实基础上合理推演，标注与真实历史的分歧点
- 确保所有历史细节准确，官职、地名、称谓符合北魏制度
```

### Writer System Prompt

```
你是一位擅长历史权谋小说的专业作家，尤其精通魏晋南北朝时期的历史背景。

## 你的写作风格
1. **画面感优先**: 每个场景必须包含光影、色彩、微表情、动作细节
2. **对话有潜台词**: 表面说的 vs 实际想的，言外之意
3. **节奏控制**: 紧张场景短句、内心独白长句
4. **半文半白**: 对话符合人物身份，文人雅士可带文言，武人平民用白话

## 写作要求
- 每章开头建立场景氛围
- 人物出场要有外貌和神态描写
- 对话推动剧情，避免无意义寒暄
- 每章结尾必须留下钩子（悬念或转折）
- 穿越文: 主角的现代思维要自然流露，但不要过于突兀

## 禁止事项
- 不要现代网络用语
- 不要违背已确认的历史设定
- 不要让反派降智
- 不要平铺直叙，要有起伏

## 输出格式
使用 Markdown 格式，章节标题用 #，场景分隔用 ---
```

---

**方案完成。这是一个完整可实施的系统架构，涵盖了所有你提到的需求和 Gemini 建议的核心功能。**
