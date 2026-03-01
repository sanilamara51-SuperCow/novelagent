"""Generate outline for qiewei_v2 - simplified version."""
import asyncio
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session

async def design():
    await session.init('qiewei_v2')

    # 直接调用 agent 拿原始响应
    from src.agents.base_agent import AgentInput
    from src.utils.persistence import NovelStorage

    instruction = """设计《窃魏》第一卷大纲（1-5 章），爽文向。
主角李曜，秀容川猎户，有火药。Ch1 穿越，Ch2-3 救公主，Ch4-5 火药炸土匪。
JSON: {"title":"窃魏","total_chapters":5,"volumes":[{"volume_number":1,"title":"卷一","chapters":[{"chapter_number":1,"title":"","summary":"","involved_characters":[],"emotional_arc":{"start":"","peak":"","end":""}}]}]}"""

    result = await session._plot_designer.process(
        AgentInput(task_type='outline_design', instruction=instruction)
    )
    print(f"Raw success: {result.success}")
    print(f"Raw error: {result.error}")
    print(f"Content len: {len(result.content)}")

    # 不管成功失败，保存原始内容
    storage = NovelStorage()
    data_to_save = {"raw_content": result.content}
    storage._save_json(
        storage._novel_dir('qiewei_v2') / 'outline' / 'outline_raw.json',
        data_to_save
    )
    print(f"\nSaved raw content to outline_raw.json")

asyncio.run(design())
