#!/usr/bin/env python3
"""从GitHub直接下载《窃魏》所需史料 - Twenty-Four-Histories特定卷

Source: https://github.com/yuanshiming/Twenty-Four-Histories
"""

import asyncio
import httpx
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/yuanshiming/Twenty-Four-Histories/master"

# 《窃魏》需要的史料文件列表
SOURCES = [
    # 魏书
    ("魏書/卷九.md", "weishu_09.txt"),
    ("魏書/卷十.md", "weishu_10.txt"),
    ("魏書/卷十一.md", "weishu_11.txt"),
    ("魏書/卷七十四.md", "weishu_74.txt"),
    ("魏書/卷七十五.md", "weishu_75.txt"),
    ("魏書/卷八十.md", "weishu_80.txt"),
    ("魏書/卷九十三.md", "weishu_93.txt"),
    ("魏書/卷九十六.md", "weishu_96.txt"),
    # 北齐书
    ("北齊書/卷一.md", "beiqishu_01.txt"),
    ("北齊書/卷二.md", "beiqishu_02.txt"),
    # 北史
    ("北史/卷五.md", "beishi_05.txt"),
    ("北史/卷六.md", "beishi_06.txt"),
    ("北史/卷四十八.md", "beishi_48.txt"),
]

RAW_DIR = Path("data/knowledge_base/raw")


async def download_file(
    client: httpx.AsyncClient, remote_path: str, local_name: str
) -> bool:
    """下载单个文件"""
    url = f"{BASE_URL}/{remote_path}"
    local_path = RAW_DIR / local_name

    try:
        resp = await client.get(url, timeout=30.0)
        resp.raise_for_status()
        local_path.write_text(resp.text, encoding="utf-8")
        print(f"[OK] {local_name} ({len(resp.text)} chars)")
        return True
    except Exception as e:
        print(f"[FAIL] {local_name}: {e}")
        return False


async def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        tasks = [download_file(client, remote, local) for remote, local in SOURCES]
        results = await asyncio.gather(*tasks)

    ok = sum(results)
    print(f"\n完成: 成功 {ok}/{len(SOURCES)}")
    return 0 if ok == len(SOURCES) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
