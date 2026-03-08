# /director-write -- 导演模式写作

这是小说导演的完整工作流。Claude 作为 Director（总控规划官），通过自身推理进行战前分析，生成 WritingBrief，指挥 Pipeline 执行写作。

## 触发方式

```
/director-write <chapter_number>
```

例如：`/director-write 1`

---

## 项目目录结构（qiewei_v2）

```
data/novels/qiewei_v2/
├── series_architecture.json       # 全书架构（5 卷 500 章）
├── chapters_1_20_outline.json     # 1-20 章详细大纲
├── outline.json                   # 完整大纲（500 章）
├── world_setting.json             # 世界设定
├── characters.json                # 角色设定
├── briefs/                        # WritingBrief 目录（导演分析输出）
│   └── ch_001.brief.json
├── chapters/                      # 章节正文（Writer LLM 输出）
│   └── ch_001.md
├── summaries/                     # 章节摘要（写完后生成）
│   └── ch_001.json
└── memory.sqlite                  # 记忆数据库
```

---

## 工作流程

### Step 1: 信息收集

读取以下数据文件（使用 `director_mode.collect_context()` 或手动读取）：

```bash
python -m src.skills.director_mode qiewei_v2 collect-context <chapter_number>
```

需要收集的核心数据：
- **全书架构**: `data/novels/qiewei_v2/series_architecture.json`
- **1-20 章大纲**: `data/novels/qiewei_v2/chapters_1_20_outline.json`（前 20 章优先使用此文件）
- **完整大纲**: `data/novels/qiewei_v2/outline.json`（20 章后使用）
- **世界设定**: `data/novels/qiewei_v2/world_setting.json`
- **角色状态**: `data/novels/qiewei_v2/characters.json` 中涉及角色的当前状态
- **上章结尾**: `data/novels/qiewei_v2/chapters/ch_{N-1}.md` 的最后 500 字
- **近 3 章摘要**: `data/novels/qiewei_v2/summaries/ch_{N-1,N-2,N-3}.json`

### Step 2: 导演分析（Claude 自身推理，不调 LLM API）

基于收集到的数据，分析以下维度：

#### 2.1 节奏判断
- 近 3 章的紧张度趋势如何？是在爬升还是回落？
- 本章处于什么位置？（蓄力/爆发/过渡/高潮）
- `target_tension` 应该是多少？（1-10）

#### 2.2 爽点设计（番茄核心）
- 本章的核心矛盾是什么？（从大纲 summary 提取）
- 应该安排几个爽点？（根据目标字数，每 800-1000 字一个）
- 每个爽点的具体内容是什么？（必须与剧情绑定，不能套模板）
- 爽点类型选择要与剧情匹配，不要机械轮转

#### 2.3 多巴胺循环
- **压抑点**: 本章主角面临什么困境？（具体到场景和情境）
- **爆发点**: 靠什么反转？（必须有逻辑基础，不能突然开挂）
- **收获点**: 反转后的具体收获是什么？

#### 2.4 卡点（Cliffhanger）
- 本章结尾悬念是什么？（必须从大纲下一章的核心矛盾反推）
- 卡点类型选择：`danger` / `discovery` / `countdown` / `mirror` / `reveal`
- 具体的卡点句式构思

#### 2.5 信息差利用
- 读者知道但主角不知道的信息有哪些？
- 主角知道但其他角色不知道的信息有哪些？
- 本章是否有机会制造新的信息差？

#### 2.6 感官密度
- 本章的主要场景环境（视觉/听觉/嗅觉/触觉的重点）
- 哪些感官细节能强化情绪？（比如紧张时聚焦心跳和呼吸）

#### 2.7 对话张力
- 本章的核心对话场景是什么？
- 潜台词设计：表面说什么 vs 实际想什么
- 配角反应层次：除了主角，围观者怎么反应？

#### 2.8 视角结构
- 本章用几个视角？（主角/反派/旁观者/全知）
- 每个视角的目的是什么？
- 视角切换是否能制造悬念？

### Step 3: 生成 WritingBrief JSON

将分析结果输出为 JSON，保存到：
```
data/novels/qiewei_v2/briefs/ch_{NNN}.brief.json
```

#### WritingBrief JSON 模板

```json
{
  "chapter_number": 1,
  "chapter_title": "猎户与火药",
  "target_word_count": 3000,
  "target_tension": 6,

  "narrative_rhythm": {
    "position": "opening",
    "recent_tensions": [],
    "reasoning": "全书第 1 章，需要快速建立危机感和金手指期待"
  },

  "opening": {
    "style": "action",
    "hook": "直接开场：李曜在小屋中醒来，头痛欲裂，窗外已有马蹄声和喊杀声",
    "first_sentence_hint": "以危机开场，不要风景描写，直接进入情境"
  },

  "shuangdian_nodes": [
    {
      "position_hint": "前 500 字",
      "type": "reveal",
      "description": "发现火药原料（硝石=墙霜、硫磺=石硫黄），专业碾压的期待感",
      "intensity": 5
    },
    {
      "position_hint": "1500-2000 字",
      "type": "power_up",
      "description": "火药试爆成功，超越时代的力量展示",
      "intensity": 7
    },
    {
      "position_hint": "2800-3000 字",
      "type": "mystery",
      "description": "神秘少女撞门登场，浑身是血",
      "intensity": 6
    }
  ],

  "dopamine_cycle": {
    "suppress": "穿越醒来，身处陌生破屋，外面有马匪搜山，生命威胁",
    "explosion": "发现火药原料并试爆成功，掌握超越时代的力量",
    "harvest": "但神秘少女闯入，新的未知危机"
  },

  "cliffhanger": {
    "type": "discovery",
    "content": "敲门声响起，一个浑身是血的锦绣少女闯进来：'快开门！他们追来了！'",
    "next_chapter_hook": "少女身份揭晓（第 2 章：平城公主元玉奴）"
  },

  "information_asymmetry": [
    {
      "who_knows": "李曜",
      "who_doesnt": "任何人",
      "what": "现代军械工程师知识，火药配方和威力",
      "tension_effect": "读者期待他如何利用火药破局"
    },
    {
      "who_knows": "读者",
      "who_doesnt": "李曜",
      "what": "原主为何有硝石硫磺——背后有隐情",
      "tension_effect": "悬念伏笔"
    }
  ],

  "sensory_focus": {
    "primary": "视觉：破旧小屋、墙上的白霜（硝石结晶）、陶罐里的黄色粉末（硫磺）",
    "secondary": "听觉：窗外的马蹄声、喊杀声、风吹窗户的吱呀声",
    "tactile": "粗糙的木床、冰冷的猎刀、温热的陶罐、硝石的苦涩味"
  },

  "dialogue_tension": {
    "core_confrontation": "无（本章主要是李曜独处）",
    "subtext": "李曜内心独白：分析处境、回忆专业知识",
    "bystander_reactions": []
  },

  "pov_structure": [
    {"pov": "protagonist", "purpose": "李曜穿越后的适应和金手指发现", "weight": "100%"}
  ],

  "foreshadowing": {
    "plant": [
      "墙上的硝石、陶罐里的硫磺——原主为何有这些？（后续揭露原主父亲是方士）",
      "猎户身份——李曜后续用猎弓杀人合理"
    ],
    "payoff": []
  },

  "world_context": "北魏正光四年（523 年），六镇起义前一年，边境动荡，马匪横行",

  "character_notes": {
    "李曜": {
      "current_state": "刚穿越，身份是秀容川猎户，父母双亡，独居",
      "voice": "冷静、理性，军械工程师思维",
      "goal": "活下去，利用专业知识在这个时代立足"
    }
  },

  "scene_plan": [
    {
      "scene": 1,
      "purpose": "开场：李曜醒来，原主记忆涌入",
      "length": "0-500 字",
      "focus": "快速交代穿越，不要拖沓"
    },
    {
      "scene": 2,
      "purpose": "查看屋内物品，发现火药原料",
      "length": "500-1200 字",
      "focus": "专业细节：硝石=墙霜，硫磺=石硫黄，木炭"
    },
    {
      "scene": 3,
      "purpose": "配制火药，试爆",
      "length": "1200-2000 字",
      "focus": "试爆过程，威力展示"
    },
    {
      "scene": 4,
      "purpose": "马匪逼近，少女撞门",
      "length": "2000-3000 字",
      "focus": "危机感 + 悬念"
    }
  ],

  "ai_trace_avoidance": [
    "不要使用 em-dash（——）过度",
    "不要使用'他不禁想到'等偷懒过渡",
    "不要重复前文信息",
    "不要超过 100 字的纯风景描写",
    "不要使用英文词汇"
  ]
}
```

### Step 4: 调用 Python CLI 执行写作

保存 Brief 后，执行：

```bash
python -m src.skills.director_mode qiewei_v2 write-with-brief <chapter_number>
```

Brief 文件路径：`data/novels/qiewei_v2/briefs/ch_{NNN}.brief.json`

### Step 5: 语义级审查

读取生成的章节 `data/novels/qiewei_v2/chapters/ch_{NNN}.md`，逐项检查：

#### 审查维度

**1. 大纲忠实度**
- 大纲中的每个 `key_scene` 是否都有对应场景？
- 大纲 summary 中的核心事件是否发生？
- 是否有大纲外的重大情节添加？

**2. WritingBrief 执行度**
- 每个 `shuangdian_node` 的 description 是否体现？
- `dopamine_cycle` 的三段式是否完整？
- `cliffhanger` 是否按设计收尾？
- `information_asymmetry` 是否在文本中体现？

**3. 连续性**
- 与上章结尾是否自然衔接？
- 角色的伤势/情绪/位置是否与前文一致？
- 是否出现了前文未铺垫的能力/物品/关系？

**4. 番茄爆款五维评估（1-10 评分）**

| 维度 | 评分标准 |
|------|---------|
| 感官密度 | 场景描写是否有视觉/听觉/触觉细节？还是只有对话？ |
| 对话张力 | 核心对话是否有潜台词？是否有话外之意？还是直白无趣？ |
| 信息差利用 | 是否制造了"读者知道但角色不知道"的紧张感？ |
| 配角反应层次 | 配角是否有存在感？是否只是"众人震惊"的道具？ |
| 压抑深度 | suppress 阶段是否足够压抑？还是一笔带过直接到爆发？ |

**5. AI 痕迹检测**
- 是否有 em-dash（——）的过度使用？
- 是否有"他不禁想到"等偷懒过渡？
- 是否有重复前文信息的段落？
- 是否有"众人皆惊"等套路化反应？
- 环境描写是否超过 100 字纯风景？

#### 通过标准

- **大纲忠实度**: 所有 key_scene 必须覆盖
- **WritingBrief 执行度**: shuangdian_nodes 全部体现，cliffhanger 到位
- **连续性**: 无硬伤
- **番茄五维**: 每个维度 >= 5 分，平均 >= 6 分
- **AI 痕迹**: 无明显痕迹
- **字数**: 2500-3500 字

### Step 6: 决策

**通过** → 调用 `update-memory`：
```bash
python -m src.skills.director_mode qiewei_v2 update-memory <chapter_number>
```
生成的摘要保存到：`data/novels/qiewei_v2/summaries/ch_{NNN}.json`

**不通过** → 生成修改意见，调用 `revise`：
```bash
python -m src.skills.director_mode qiewei_v2 revise <chapter_number> --feedback "..."
```

修改意见格式示例：
```
审查结果：不通过

问题 1：[感官密度不足] 第二个场景（元天穆会面）全程只有对话，缺少军帐环境的视觉和听觉细节。建议在对话间隙加入烛光、风声、铠甲碰撞等描写。

问题 2：[压抑不够] suppress 阶段只用了 200 字就跳到 explosion，读者没有感受到"被质疑/被轻视"的压力。建议扩展元天穆手下嘲笑的场景到 300-400 字。

问题 3：[配角消失] brief 中要求侍卫长从"不屑"转为"警觉"，但文中侍卫长完全没有出现。
```

---

## 快速命令参考

```bash
# 查看项目状态
python -m src.skills.director_mode qiewei_v2 status

# 收集某章上下文（输出 JSON）
python -m src.skills.director_mode qiewei_v2 collect-context <chapter_number>

# 使用已保存的 Brief 写作
python -m src.skills.director_mode qiewei_v2 write-with-brief <chapter_number>

# 带反馈重写
python -m src.skills.director_mode qiewei_v2 revise <chapter_number> --feedback "修改意见..."

# 更新记忆（生成摘要）
python -m src.skills.director_mode qiewei_v2 update-memory <chapter_number>

# 查看某章状态
python -m src.skills.director_mode qiewei_v2 chapter-status <chapter_number>
```

---

## 文件路径对照表

| 文件类型 | 路径 | 用途 |
|----------|------|------|
| 全书架构 | `data/novels/qiewei_v2/series_architecture.json` | 5 卷 500 章总体设计 |
| 详细大纲 (1-20) | `data/novels/qiewei_v2/chapters_1_20_outline.json` | 前 20 章逐章大纲 |
| 完整大纲 | `data/novels/qiewei_v2/outline.json` | 500 章完整大纲 |
| 世界设定 | `data/novels/qiewei_v2/world_setting.json` | 时代背景、势力、人物 |
| 角色设定 | `data/novels/qiewei_v2/characters.json` | 角色卡片 |
| WritingBrief | `data/novels/qiewei_v2/briefs/ch_{NNN}.brief.json` | 导演分析输出 |
| 章节正文 | `data/novels/qiewei_v2/chapters/ch_{NNN}.md` | Writer LLM 输出 |
| 章节摘要 | `data/novels/qiewei_v2/summaries/ch_{NNN}.json` | 写完后生成 |
| 记忆数据库 | `data/novels/qiewei_v2/memory.sqlite` | 长期记忆 |

---

## 番茄爆款五维详细说明

### 1. 感官密度（Sensory Density）

**低分 (1-3)**: 只有对话和动作，无环境细节
**中分 (4-6)**: 有基本的环境描写，但不够沉浸
**高分 (7-10)**: 多感官融合，读者能"看到/听到/闻到/触到"场景

示例（高分）：
> 烛光在铠甲上跳动，冷光刺目。帐外风声呼啸，夹杂着远处战马的嘶鸣。李曜伸手去拿那张羊皮纸，指尖触到粗糙的纹理和尚未干透的墨迹，冰凉。

### 2. 对话张力（Dialogue Tension）

**低分 (1-3)**: 直白问答，无潜台词
**中分 (4-6)**: 部分对话有弦外之音
**高分 (7-10)**: 每句对话都有表面意思和真实意图的分裂

示例（高分）：
> "先生真才实学，令人佩服。"元天穆笑着说，目光却没离开李曜的手。
> （潜台词：你在试探我是否真的懂这些）
>
> 李曜放下笔："大将军谬赞。"
> （潜台词：我知道你在试探，但我不会露馅）

### 3. 信息差利用（Information Asymmetry）

**低分 (1-3)**: 所有角色知道的信息相同
**中分 (4-6)**: 有基本信息差，但没有制造紧张感
**高分 (7-10)**: 读者知道但角色不知道，或角色知道但互相隐瞒

示例（高分）：
> 李曜不知道的是，元天穆袖中的手已经按上了刀柄。
> 读者知道：元天穆在试探
> 李曜不知道：自己随时可能没命

### 4. 配角反应层次（Supporting Character Reactions）

**低分 (1-3)**: 配角是道具人，只有"众人皆惊"
**中分 (4-6)**: 配角有独立反应，但单一
**高分 (7-10)**: 配角有层次变化的反应链

示例（高分）：
> 侍卫长的手从刀柄上滑开，眼神从轻蔑变成警觉。
> 幕僚们交换着眼神，有人低头，有人直盯着李曜。
> 角落里，一个一直闭目养神的老者睁开了眼。

### 5. 压抑深度（Suppression Depth）

**低分 (1-3)**: 一笔带过，直接跳到爆发
**中分 (4-6)**: 有压抑场景，但力度不足
**高分 (7-10)**: 压抑层层递进，读者真切感受到主角的困境

示例（高分）：
> 第一层：元天穆扫了一眼李曜的衣裳："书生？"
> 第二层：手下哄笑："这细皮嫩肉的，能造火器？"
> 第三层：元天穆把图纸推到一边："军中不养闲人。"
> 第四层：刀已经出鞘三寸，烛光照在刃上。

---

## 注意事项

1. **WritingBrief 不是束缚，是导航**：如果写作过程中有更好的灵感，可以在不违背核心爽点和卡点的前提下灵活调整

2. **爽点不是堆砌，是递进**：每个爽点应该比上一个更强，形成情绪爬升曲线

3. **信息差不是隐瞒，是悬念**：要让读者知道一些角色不知道的事，制造"替主角捏汗"的效果

4. **卡点不是结束，是钩子**：章末悬念必须让读者"不得不点下一章"

5. **感官不是装饰，是沉浸**：细节必须服务于情绪，不是为写而写
