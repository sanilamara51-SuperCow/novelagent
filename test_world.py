"""Quick test for world building."""
import asyncio
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session
from src.agents.base_agent import AgentInput

async def test():
    await session.init('qiewei_v2')

    # 短 prompt 快速测试
    desc = '北魏末年穿越爽文，主角有火药和现代军事知识，最终称帝。生成 JSON 世界观，包含 era, year_range, political_system, geography, factions 字段。'

    result = await session.build_world(desc)
    print(f"Success: {result.success}, Error: {result.error}")
    print(f"Content len: {len(result.content)}")
    if result.content:
        print(f"First 200 chars: {result.content[:200]}")

asyncio.run(test())
