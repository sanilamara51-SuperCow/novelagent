#!/usr/bin/env python3
"""从ctext.org下载《窃魏》所需史料 - 改进版

《魏书》《北齐书》《北史》特定卷
"""

import asyncio
import html
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

CTEXT_SOURCES = [
    # 魏书 - 关键卷
    ("weishu_09", "魏书", "卷九 肃宗纪", "809513", "523-528"),
    ("weishu_10", "魏书", "卷十 孝庄纪", "809514", "528-530"),
    ("weishu_11", "魏书", "卷十一 前后废帝纪", "809515", "530-534"),
    ("weishu_74", "魏书", "卷七十四 尔朱荣传", "598331", "523-530"),
    ("weishu_75", "魏书", "卷七十五 尔朱兆等传", "598332", "530-533"),
    ("weishu_80", "魏书", "卷八十 朱瑞等传", "598337", "528-534"),
    # 北齐书
    ("beiqishu_1", "北齐书", "卷一 神武帝上", "809237", "496-532"),
    ("beiqishu_2", "北齐书", "卷二 神武帝下", "809238", "532-547"),
    # 北史
    ("beishi_5", "北史", "卷五 魏本纪第五", "809488", "528-531"),
    ("beishi_6", "北史", "卷六 齐本纪上", "809489", "531-534"),
    ("beishi_48", "北史", "卷四十八 尔朱列传", "809194", "523-533"),
]

RAW_DIR = Path("data/knowledge_base/raw")
DB_PATH = Path("data/knowledge_base/source_catalog.db")


@dataclass
class SourceEntry:
    source_id: str
    work: str
    chapter: str
    ctext_id: str
    year_range: str


def clean_text(text: str) -> str:
    """清洗ctext文本"""
    # 解码HTML实体
    text = html.unescape(text)

    # 去除导航
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过导航
        if any(
            x in line
            for x in [
                "本站介紹",
                "簡介",
                "字體試驗",
                "協助",
                "常見問答",
                "使用說明",
                "工具",
                "統計",
                "數位人文",
                "登入",
                "檢索",
                "書名檢索",
                "简体",
                "English",
            ]
        ):
            continue
        # 跳过英文（以大写字母开头且包含多个英文单词）
        if re.match(r"^[A-Z][a-zA-Z\s,\.]{20,}", line):
            continue
        clean_lines.append(line)

    return "\n".join(clean_lines)


async def fetch_and_save(client: httpx.AsyncClient, entry: SourceEntry) -> bool:
    """下载并保存单个史料"""
    url = f"https://ctext.org/wiki.pl?if=gb&chapter={entry.ctext_id}"
    local_path = RAW_DIR / f"{entry.source_id}.txt"

    try:
        print(f"[下载] {entry.source_id} - {entry.chapter}...")
        resp = await client.get(url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()

        # 清洗并保存
        cleaned = clean_text(resp.text)

        if len(cleaned) < 1000:
            print(f"  [警告] 内容较短: {len(cleaned)} 字符")

        local_path.write_text(cleaned, encoding="utf-8")
        print(f"  [成功] {len(cleaned)} 字符")
        return True

    except Exception as e:
        print(f"  [失败] {e}")
        return False


async def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    entries = [SourceEntry(*args) for args in CTEXT_SOURCES]

    async with httpx.AsyncClient() as client:
        for entry in entries:
            await fetch_and_save(client, entry)
            await asyncio.sleep(3)  # 礼貌延迟

    print("\n下载完成")


if __name__ == "__main__":
    asyncio.run(main())
