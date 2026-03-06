# 小说写作技能总结 (Novel Writing Skills)

## 会话初始化
```python
from src.skills import session
await session.init('qiewei_v2')
```

---

## 核心技能 API

### 1. 状态查询
```python
status = await session.status()
# 返回：novel_id, has_world_setting, outline_chapters, chapters_written, next_chapter
```

### 2. 世界观构建
```python
# 从零构建
result = await session.build_world("北魏末年穿越小说，主角是军械工程师")

#  refining 已有设定
result = await session.refine_world("增加六镇起义的历史细节")
```

### 3. 大纲设计
```python
# 基于世界观设计完整大纲
result = await session.design_outline("设计 500 章大纲，分 7 卷")

# 查询大纲
outline = await session.get_outline()  # 全部
chapter_outline = await session.get_outline(3)  # 特定章节
```

### 4. 章节写作（完整 Pipeline）
```python
result = await session.write_chapter(3)
# Pipeline: draft → consistency_check → polish → risk_assess → memory_update
# 返回：success, content, data{word_count, consistency, risk}
```

### 5. 分步执行
```python
# 初稿
draft = await session.draft_chapter(3)

# 一致性检查
check = await session.check_consistency(3)
# 返回：passed, issues[]

# 润色
polish = await session.polish_chapter(3, instructions="增加动作描写")

# 风险评估
risk = await session.assess_risk(3)
# 返回：tension_score, villain_iq, protagonist_difficulty, arc_match, rewrite_required

# 更新记忆
await session.update_memory(3)
```

### 6. 读取辅助
```python
# 读取章节
chapter = await session.get_chapter(1)

# 读取世界观
world = await session.get_world_setting()

# 读取记忆上下文
ctx = await session.get_memory_context(3)
```

### 7. 修订
```python
# 根据反馈修订
result = await session.revise_chapter(3, "增加公主的心理描写")

# 一致性修订（内部调用）
result = await session._rewrite_for_consistency(3, issues)
```

### 8. NPC 辩论（沙盒模拟）
```python
result = await session.run_debate(
    topic="是否应该救公主",
    npcs=[
        {"name": "李曜", "stance": "理性派"},
        {"name": "元玉奴", "stance": "求生派"}
    ],
    context="被马匪追杀的山洞中",
    max_rounds=3
)
```

---

## 工作流程

### 完整写作流程
```
1. session.init(novel_id)
2. session.status()  ← 检查进度
3. session.write_chapter(N)  ← 自动完成全 pipeline
4. 检查结果：
   - result.success
   - result.data['risk'].get('rewrite_required')
   - result.data['consistency'].get('issues')
```

### 批量写作
```python
for ch in range(1, 21):
    result = await session.write_chapter(ch)
    if not result.success:
        print(f"第{ch}章失败：{result.error}")
        break
    print(f"第{ch}章完成：{result.data.get('word_count')}字")
```

---

## 配置管理

### 文风配置
位置：`config/prompts/writer.txt`, `config/prompts/style_polisher.txt`

关键配置项：
- 文风：白话文/半文半白/文言文
- 节奏：紧张场景短句，抒情场景长句
- 画面感：光影、色彩、微表情、动作细节

### 模型配置
位置：`config/settings.yaml`

每章写作耗时：约 5-8 分钟
- Draft: ~2 分钟
- Consistency: ~1 分钟
- Polish: ~2 分钟
- Risk: ~30 秒
- Memory: ~30 秒

---

## 数据结构

### SkillResult
```python
@dataclass
class SkillResult:
    success: bool
    content: str
    data: dict[str, Any]
    error: str
```

### 章节输出
- 保存位置：`data/novels/{novel_id}/chapters/ch_{N:03d}.md`
- 元数据：`data/novels/{novel_id}/chapters/ch_{N:03d}.meta.json`
- 摘要：`data/novels/{novel_id}/summaries/ch_{N:03d}.json`

---

## 注意事项

### 必须调用顺序
1. `session.init()` 必须先于所有其他调用
2. `write_chapter()` 依赖 `outline` 存在
3. `check_consistency/polish/assess_risk` 依赖章节已写入

### 常见错误
- `No outline found`: 先运行 `design_outline()`
- `Chapter not found`: 确认章节已 `draft` 或 `write`
- `Call session.init first`: 单例未初始化

### 性能优化
- 批量写作时使用后台任务
- 每章完成后检查 `risk.rewrite_required`
- 一致性检查失败会自动重试（默认 1 次）

---

## 实际使用示例

### 启动新项目
```python
from src.skills import session

# 1. 初始化
await session.init('my_novel')

# 2. 构建世界观
await session.build_world("现代医生穿越唐朝，成为孙思邈弟子")

# 3. 设计大纲
await session.design_outline("设计 300 章大纲，分 5 卷")

# 4. 开始写作
for ch in range(1, 11):
    result = await session.write_chapter(ch)
    print(f"Ch{ch}: {result.data.get('word_count')}字")
```

### 检查进度
```python
status = await session.status()
print(f"已写：{status.data['chapters_written']}章")
print(f"下一张：{status.data['next_chapter']}")
```

### 读取已写章节
```python
chapter = await session.get_chapter(1)
print(chapter.content[:500])  # 预览前 500 字
```

---

## 写作模式配置

### 三种写作模式

在 `config/settings.yaml` 中设置 `project.writing_mode`:

```yaml
project:
  writing_mode: "quality"  # quality / volume / hybrid
```

| 维度 | quality (历史正剧) | volume (商业快消) | hybrid (平衡) |
|------|-------------------|------------------|--------------|
| **单章字数** | 2500-3500 字 | 1500-2000 字 | 2000-2800 字 |
| **冲突密度** | 0.5 次/千字 | 1.0 次/千字 | 0.7 次/千字 |
| **卡点模式** | soft 悬念 | hard 强悬念 | soft 悬念 |
| **质量检查** | 完整 pipeline | 快速模式 | 标准 pipeline |
| **适用场景** | 《窃魏》等历史考据 | 番茄流量文 | 兼顾质量与节奏 |

### 模式行为

**quality 模式** (历史正剧):
- 保留完整质量 pipeline：`draft → consistency_check → style_polish → risk_assess`
- 一致性检查失败会自动重试
- 注重历史准确性（官职/年龄/事件）
- 文笔打磨更精细

**volume 模式** (商业快消):
- 跳过 `style_polish` 环节
- 一致性检查失败不自动重试
- 节奏更快，爽点密度更高
- 适合批量快速生产

**hybrid 模式** (平衡):
- 保留 `style_polish` 和一致性重试
- 节奏密度介于两者之间
- 兼顾文学性与可读性

---

### CLI 命令

```bash
# 设置写作模式
python -m src.main mode --novel-id qiewei_001 --mode quality
python -m src.main mode --novel-id qiewei_001 --mode volume
python -m src.main mode --novel-id qiewei_001 --mode hybrid

# 查看当前模式
python -m src.main mode --novel-id qiewei_001 --show

# 批量写作（自动根据模式调整 pipeline）
python -m src.main batch --novel-id qiewei_001 --count 10 --start 1

# 续写大纲
python -m src.main extend --novel-id qiewei_001 --add-chapters 50 --arc-theme "进京篇"
```

---

### 使用示例

#### 开启新模式写作
```python
from src.skills import session

await session.init('qiewei_001')

# 单一 API，根据配置自动调整行为
result = await session.write_chapter(5)

print(f"字数：{result.data.get('word_count')}")
print(f"质量评分：{result.data.get('quality_score')}")
```

#### 批量写作
```python
# 自动根据写作模式调整 pipeline
result = await session.batch_write(start=1, count=10)

print(f"完成章节数：{result.data.get('written_count')}")
print(f"总字数：{result.data.get('total_words'):,}")
```

#### 续写大纲
```python
# 无限续写 - 修改全局提示词引入新地图/新反派
result = await session.extend_story(
    add_chapters=50,
    new_arc_theme="进京篇"  # 可选：新篇章主题
)

print(f"新增章节：{result.data.get('added_chapters')}")
print(f"总章节数：{result.data.get('total_chapters')}")
print(f"新章节范围：{result.data.get('new_chapter_range')}")
```

---

### 节奏优化器 Agent

位置：`src/agents/pacing_optimizer.py`

职责：
- 检测并调整节奏密度（根据写作模式：quality/volume/hybrid）
- 优化章节结尾悬念（根据 cliffhanger_mode: soft/hard）
- 识别拖沓内容并提供删减建议

配置：
```yaml
agents:
  pacing_optimizer:
    model: "deepseek-chat"
    max_tokens: 4096
```

提示词：`config/prompts/pacing_optimizer.txt`

---
