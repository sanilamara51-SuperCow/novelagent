# UTILS KNOWLEDGE BASE

**Parent:** `../src/AGENTS.md`

## OVERVIEW
工具模块，提供日志、持久化、大纲加载、异步IO、范围规划等通用能力。

## STRUCTURE
```
utils/
├── logger.py           # 日志配置
├── persistence.py      # 状态持久化(JSON/SQLite)
├── outline_loader.py   # 大纲加载/解析
├── range_planner.py    # 章节范围规划
├── async_io.py         # 异步IO工具
└── __init__.py
```

## CODE MAP

| Symbol | File | Role |
|--------|------|------|
| `get_logger()` | `logger.py` | 获取结构化日志器 |
| `StatePersistence` | `persistence.py` | 状态读写 |
| `OutlineLoader` | `outline_loader.py` | 大纲JSON解析 |
| `RangePlanner` | `range_planner.py` | 批量章节规划 |

## USAGE

### 日志
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Starting workflow", extra={"phase": "init"})
```

```python
from src.utils.persistence import StatePersistence

persistence = StatePersistence(project_path)
```
```python
from src.utils.persistence import StatePersistence = StatePersistence(project_path)
state = persist

persist.load()
persist.save(state)
```

### 大纲加载
```python
from src.utils.outline_loader import OutlineLoader

loader = OutlineLoader(project_path)
outline = loader.load()
```

## ANTI-PATTERNS
- **勿直接print**: 用`logger`替代
- **勿同步文件IO**: 用`async_io`包装
