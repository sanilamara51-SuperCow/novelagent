# SRC KNOWLEDGE BASE

**Parent:** `../AGENTS.md`

## OVERVIEW
核心源码目录，包含Agent实现、编排、状态机、记忆系统、RAG服务。

## STRUCTURE
```
src/
├── agents/          # 7个Agent实现
├── memory/          # 三层记忆系统
├── knowledge/       # RAG/Embedding
├── models/          # LLM客户端
├── utils/           # 工具
├── main.py          # CLI入口
├── orchestrator.py  # 编排器
├── state_machine.py # 状态机
├── context_assembler.py
├── config.py        # 配置加载
└── review.py        # 人机交互审查
```

## WHERE TO LOOK
| Task | File | Notes |
|------|------|-------|
| 运行CLI | `main.py` | `python -m src.main` |
| 工作流逻辑 | `orchestrator.py` | 各Phase实现 |
| 状态定义 | `state_machine.py` | NovelStateMachine类 |
| Agent基类 | `agents/base_agent.py` | 所有Agent继承此类 |
| 上下文组装 | `context_assembler.py` | Writer专用上下文 |

## CONVENTIONS

### 文件组织
- 每个Agent独立文件，文件名=`{snake_case}.py`
- Agent类名=`{PascalCase}Agent`
- 所有Agent必须能被`orchestrator.py`导入

### 异步模式
- 所有I/O操作必须async
- LLM调用统一通过`LLMClient.acompletion()`
- 状态机回调支持async (`on_enter_state`)

## ANTI-PATTERNS
- **勿同步阻塞**: 禁止`time.sleep()`, 用`asyncio.sleep()`
- **勿直接print**: 用`rich.console`或logger
- **勿相对导入上级**: 统一用`from src.xxx import`

## COMMANDS
```bash
# 从novelagent目录运行
python -m src.main new      # 新建小说
python -m src.main resume 1 # 恢复小说
python -m src.main status   # 查看状态
```
