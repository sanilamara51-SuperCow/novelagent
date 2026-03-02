# Director 模式使用指南

## 快速启动

```python
from src.skills.director_mode import director_mode
import asyncio

async def main():
    # 1. 激活 Director 模式
    report = await director_mode.activate("qiewei_v2")

    # 2. 查看导演报告
    print(f"已写章节：{report.written_chapters}")
    print(f"节奏分析：{report.rhythm_analysis}")
    print(f"伏笔状态：{report.foreshadowing_status}")

    # 3. 生成第 11 章写作简报
    brief = await director_mode.generate_writing_brief(11)
    print(f"目标紧张度：{brief.target_tension}")
    print(f"需要回收的伏笔：{brief.foreshadowing_payoff}")

    # 4. 写作
    result = await director_mode.write_chapter(11, auto_review=True)

asyncio.run(main())
```

## CLI 用法

```bash
# 查看状态
python -m src.skills.director_mode qiewei_v2 status

# 写一章
python -m src.skills.director_mode qiewei_v2 write 11

# 批量写
python -m src.skills.director_mode qiewei_v2 batch 11 15

# 导演报告
python -m src.skills.director_mode qiewei_v2 report
```

## Director 核心功能

### 1. 伏笔账本 (ForeshadowingLedger)

**自动追踪伏笔的埋设和回收**

```python
# 埋设伏笔
memory.long_term.add_foreshadow(
    foreshadow_id="ch01_foreshadow_1",
    description="猎户家中遗留的硝石、硫磺",
    planted_chapter=1,
    expected_payoff_range=[3, 5],  # 预期在第 3-5 章回收
    importance="major"
)

# 查询到期伏笔
due = memory.long_term.get_due_foreshadowing(current_chapter=4)
# 返回：[{foreshadow_id, description, is_overdue, ...}]
```

**Director 自动在 WritingBrief 中包含伏笔指令**：
- `foreshadowing_plant`: 需要埋设的伏笔
- `foreshadowing_payoff`: 需要回收的伏笔（含到期警告）

### 2. 节奏追踪 (RhythmTracker)

**记录每章紧张度 (1-10)，分析全局节奏**

```python
# 记录紧张度
memory.long_term.record_tension(chapter_id=4, tension_score=9)

# 节奏分析
analysis = memory.long_term.get_rhythm_analysis()
# 返回：{
#   "recent_tensions": [9, 5, 7],
#   "trend": "falling",  # rising | falling | flat | volatile
#   "suggestion": "连续高潮后需要回落"
# }
```

**Director 自动根据节奏设定目标紧张度**：
- 连续 3 章高潮 (avg>7) → 目标紧张度 4
- 连续 3 章平淡 (avg<4) → 目标紧张度 7
- 正常 → 目标紧张度 5

### 3. 多线叙事 (StoryThreads)

**追踪多条故事线的进展**

```python
# 添加故事线
memory.long_term.add_story_thread(
    thread_id="main_plot",
    name="主角崛起线",
    pov_character="李曜",
    arc="从猎户到权臣的崛起"
)

# 更新进展
memory.long_term.update_thread_progress("main_plot", chapter_id=10)

# 检查是否有线程被遗忘
warnings = memory.long_term.get_thread_gap_warning(max_gap=5)
# 返回：[{thread_id, name, issue: "已 7 章未出现"}]
```

### 4. WritingBrief（写作简报）

**Director 每章开写前生成的精炼指令**

```python
WritingBrief:
  chapter_outline: str          # 本章大纲
  opening_hook: str             # 上章悬念
  closing_hook: str             # 本章结尾悬念
  foreshadowing_plant: []       # 需要埋设的伏笔
  foreshadowing_payoff: []      # 需要回收的伏笔
  characters: []                # 出场角色简报
  scenes: []                    # 场景约束
  target_tension: int           # 目标紧张度 (1-10)
  sensory_focus: str            # 感官描写重点
  information_asymmetry: []     # 信息不对称表
```

## 已记录的状态（《窃魏》前 6 章）

### 节奏序列
| 章节 | 1 | 2 | 3 | 4 | 5 | 6 |
|------|---|---|---|---|---|---|
| 紧张度 | 6 | 7 | 8 | 9 | 5 | 7 |

**分析**：第 4 章高潮后已回落，第 6 章开始新的上升

### 伏笔账本
| ID | 描述 | 埋设章 | 预期回收 | 状态 |
|----|------|--------|----------|------|
| ch01_foreshadow_1 | 硝石、硫磺 | 1 | 3-5 | 已超期 |
| ch02_foreshadow_1 | 元玉奴身世 | 2 | 5-8 | 已超期 |
| ch06_foreshadow_1 | 崔孝芬救援 | 6 | 7-10 | 待回收 |

**建议**：前两个伏笔已回收（火药首秀、身世揭露），可标记为 `paid_off`

## 下一步

1. **标记已回收的伏笔**：
   ```python
   memory.long_term.mark_foreshadow_paid_off("ch01_foreshadow_1", payoff_chapter=4)
   memory.long_term.mark_foreshadow_paid_off("ch02_foreshadow_1", payoff_chapter=6)
   ```

2. **写第 11 章**：
   ```python
   result = await director_mode.write_chapter(11)
   ```

3. **完善 CharacterVoice**：为每个角色添加语音卡，让对话更有区分度
