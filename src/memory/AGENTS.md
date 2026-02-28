# MEMORY KNOWLEDGE BASE

**Parent:** `../src/AGENTS.md`

## OVERVIEW
三层记忆架构：短期记忆(Context)+长期记忆(JSON/SQLite)+外部记忆(RAG向量库)。

## STRUCTURE
```
memory/
├── memory_manager.py    # 统一入口
├── short_term.py        # 短期记忆(上下文窗口)
├── long_term.py         # 长期记忆(角色/事件)
├── rag_retriever.py     # RAG检索
└── summarizer.py        # 章节摘要生成
```

## ARCHITECTURE
```
┌─────────────────────────────────────────┐
│           MemoryManager                 │
├─────────────┬─────────────┬─────────────┤
│  短期记忆    │  长期记忆    │   RAG       │
│  (Context)   │  (JSON/SQL) │  (ChromaDB) │
├─────────────┼─────────────┼─────────────┤
│ • 当前章节   │ • 角色卡片   │ • 史料知识库 │
│ • 前3章摘要 │ • 事件时间线 │ • 已写章节   │
│ • 当前任务   │ • 人物关系图 │             │
└─────────────┴─────────────┴─────────────┘
```

## USAGE

### 获取Writer上下文
```python
context = memory_manager.get_writer_context(chapter_outline)
# 返回: 角色状态、前情摘要、相关史料等
```

### 章节后更新
```python
await memory_manager.update_after_chapter(chapter, outline)
# 自动: 生成摘要、更新角色状态、索引到RAG
```

## CONVENTIONS
- 短期记忆容量：~4K tokens
- 长期记忆：无限制，JSON文件存储
- RAG：GB级别，ChromaDB
- 摘要窗口：最近3章

## ANTI-PATTERNS
- **勿直接操作RAG**: 通过`MemoryManager`统一接口
- **勿跳过摘要**: 每章必须生成摘要更新长期记忆
- **勿同步加载**: 所有记忆操作必须async
