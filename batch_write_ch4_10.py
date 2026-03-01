#!/usr/bin/env python3
import asyncio
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session

async def batch_write(start_ch, end_ch):
    await session.init('qiewei_v2')

    for ch in range(start_ch, end_ch + 1):
        print(f"\n{'='*60}")
        print(f"开始写第{ch}章")
        print(f"{'='*60}\n")

        result = await session.write_chapter(ch)

        if result.success:
            wc = result.data.get('word_count', '?')
            risk = result.data.get('risk', {})
            rewrite = risk.get('rewrite_required', False)

            status = "✓" if not rewrite else "⚠ (需修订)"
            print(f"{status} 第{ch}章完成 ({wc}字)")

            if rewrite:
                print(f"  风险标记：{risk.get('suggestions', [])}")
        else:
            print(f"✗ 第{ch}章失败：{result.error}")
            break

    print(f"\n{'='*60}")
    print("批量写作完成！")
    print(f"{'='*60}")

asyncio.run(batch_write(4, 10))
