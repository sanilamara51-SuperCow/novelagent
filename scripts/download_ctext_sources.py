#!/usr/bin/env python3
"""从ctext.org下载《窃魏》所需史料

《魏书》《北齐书》《北史》特定卷
"""

import asyncio
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ctext chapter IDs for needed volumes
# From SOURCE_MAP_DEEP_V2.md
CTEXT_SOURCES = [
    # 魏书
    ("weishu_09", "魏书", "卷九 肃宗纪", "809513", "523-528"),
    ("weishu_10", "魏书", "卷十 孝庄纪", "809514", "528-530"),
    ("weishu_11", "魏书", "卷十一 前后废帝纪", "809515", "530-534"),
    ("weishu_74", "魏书", "卷七十四 尔朱荣传", "598331", "523-530"),
    ("weishu_75", "魏书", "卷七十五 尔朱兆等传", "598332", "530-533"),
    ("weishu_80", "魏书", "卷八十 朱瑞等传", "598337", "528-534"),
    ("weishu_93", "魏书", "卷九十三 恩幸传", "794963", "-"),
    ("weishu_96", "魏书", "卷九十六 僭伪传", "794970", "523-528"),
    # 北齐书
    ("beiqishu_1", "北齐书", "卷一 神武帝上", "809237", "496-532"),
    ("beiqishu_2", "北齐书", "卷二 神武帝下", "809238", "532-547"),
    # 北史
    ("beishi_5", "北史", "卷五 魏本纪第五", "809488", "528-531"),
    ("beishi_6", "北史", "卷六 齐本纪上", "809489", "531-534"),
    ("beishi_48", "北史", "卷四十八 列传第三十六", "809194", "523-533"),
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


def ensure_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ctext_sources (
            source_id TEXT PRIMARY KEY,
            work TEXT NOT NULL,
            chapter TEXT NOT NULL,
            ctext_id TEXT NOT NULL,
            year_range TEXT,
            local_path TEXT,
            status TEXT NOT NULL,
            content_length INTEGER,
            fetched_at TEXT
        )
        """
    )
    conn.commit()


def save_status(
    conn: sqlite3.Connection,
    entry: SourceEntry,
    local_path: str | None,
    status: str,
    content_length: int | None,
) -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO ctext_sources 
        (source_id, work, chapter, ctext_id, year_range, local_path, status, content_length, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry.source_id,
            entry.work,
            entry.chapter,
            entry.ctext_id,
            entry.year_range,
            local_path,
            status,
            content_length,
            fetched_at,
        ),
    )
    conn.commit()


async def fetch_ctext(client: httpx.AsyncClient, ctext_id: str) -> str:
    """Fetch text from ctext.org"""
    # Try wiki API first
    url = f"https://ctext.org/wiki.pl?if=gb&chapter={ctext_id}"
    resp = await client.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()

    # Extract main content - ctext uses specific HTML structure
    text = resp.text

    # Simple cleanup - remove HTML tags
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&amp;", "&", text)

    # Clean up whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


async def download_source(
    client: httpx.AsyncClient, conn: sqlite3.Connection, entry: SourceEntry
) -> bool:
    """Download a single source"""
    try:
        print(f"[DOWNLOAD] {entry.source_id} - {entry.chapter}...")
        text = await fetch_ctext(client, entry.ctext_id)

        if len(text) < 500:
            raise ValueError(f"Content too short: {len(text)} chars")

        local_path = RAW_DIR / f"{entry.source_id}.txt"
        local_path.write_text(text, encoding="utf-8")

        save_status(conn, entry, str(local_path), "downloaded", len(text))
        print(f"[OK] {entry.source_id} ({len(text)} chars)")
        return True

    except Exception as e:
        print(f"[FAIL] {entry.source_id}: {e}")
        save_status(conn, entry, None, f"failed: {e}", None)
        return False


async def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    ensure_db(conn)

    entries = [
        SourceEntry(sid, work, chapter, cid, year)
        for sid, work, chapter, cid, year in CTEXT_SOURCES
    ]

    # Add delay between requests to be polite
    results = []
    async with httpx.AsyncClient() as client:
        for entry in entries:
            result = await download_source(client, conn, entry)
            results.append(result)
            await asyncio.sleep(2)  # Be polite to ctext.org

    conn.close()

    ok = sum(results)
    print(f"\n完成: 成功 {ok}/{len(entries)}")
    return 0 if ok == len(entries) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
