#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write Chapter 1 of qiewei_v2 using skills API"""

import os
import sys
import io
import asyncio

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session

async def write_ch1():
    await session.init('qiewei_v2')

    print("="*60)
    print("开始写第 1 章：惊雷落秀容")
    print("="*60)

    # 用 write_chapter 完整 pipeline
    result = await session.write_chapter(1)

    print(f"\nSuccess: {result.success}")
    if result.success:
        print(f"Word count: {result.data.get('word_count', 'N/A')}")
        print(f"\n第 1 章已保存到：data/novels/qiewei_v2/chapters/ch_001.md")

        # 显示开头 200 字
        content = result.content
        print(f"\n【开头预览】")
        print(content[:300] if content else "无内容")
    else:
        print(f"Error: {result.error}")

asyncio.run(write_ch1())
