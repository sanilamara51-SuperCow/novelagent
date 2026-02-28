# KNOWLEDGE KNOWLEDGE BASE

**Parent:** `../src/AGENTS.md`

## OVERVIEW
RAG知识库系统，处理史料加载、文本切分、Embedding生成、向量检索。

## STRUCTURE
```
knowledge/
├── data_loader.py        # 史料加载
├── text_chunker.py       # 文本切分(按传记/编年/条目)
├── embedding_service.py  # BAAI/bge-m3 Embedding
└── rag_retriever.py      # ChromaDB检索
```

## DATA SOURCES
- 《魏书》— 纪传体，按传切分
- 《资治通鉴》— 编年体，按年切分
- 《洛阳伽蓝记》— 地理志，按寺院切分

## USAGE

### 检索史料
```python
retriever = RAGRetriever(config)
results = await retriever.search("太和改制", top_k=5)
# 返回: 相关史料片段+元数据
```

### 加载新史料
```python
# scripts/setup_kb.py
python scripts/setup_kb.py  # 初始化/更新知识库
```

## CONVENTIONS
- Embedding模型: BAAI/bge-m3
- 切分大小: 800 tokens
- 重叠: 150 tokens
- 检索: top_k=5

## ANTI-PATTERNS
- **勿重复索引**: 检查doc_id是否存在
- **勿大段检索**: 控制chunk_size，避免上下文溢出
- **勿同步Embedding**: 用`asyncio.to_thread`包装同步模型调用
