"""Write chapters 2-5 of qiewei_v2."""
import asyncio
import sys
import os

if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session

async def write_ch2_to_5():
    await session.init('qiewei_v2')

    chapters = [
        (2, "荒原藏凤"),
        (3, "一矢定危局"),
        (4, "霹雳破重围"),
        (5, "声震秀容川"),
    ]

    for ch_num, ch_title in chapters:
        print("="*60)
        print(f"写第{ch_num}章：{ch_title}")
        print("="*60)

        result = await session.write_chapter(ch_num)

        if result.success:
            print(f"✓ 第{ch_num}章完成 ({result.data.get('word_count', '?')}字)")
        else:
            print(f"✗ 第{ch_num}章失败：{result.error}")

    print("\n" + "="*60)
    print("写作完成！")
    print("="*60)

asyncio.run(write_ch2_to_5())
