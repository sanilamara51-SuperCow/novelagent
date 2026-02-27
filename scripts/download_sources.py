from __future__ import annotations

import argparse
import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx


RAW_DIR = Path("data/knowledge_base/raw")
DB_PATH = Path("data/knowledge_base/source_catalog.db")


@dataclass(frozen=True)
class SourceEntry:
    source_id: str
    work: str
    chapter: str
    page: str
    year_range: str
    event_tags: str
    person_tags: str


SOURCES: list[SourceEntry] = [
    SourceEntry("weishu_09", "魏书", "卷九 肃宗纪", "魏書/卷九", "523-528", "six_garrisons_revolt", "xiaoming"),
    SourceEntry("weishu_10", "魏书", "卷十 孝庄纪", "魏書/卷十", "528-530", "heyin_incident,mingguang_assassination", "xiaozhuang,erzhurong"),
    SourceEntry("weishu_11", "魏书", "卷十一 前后废帝纪", "魏書/卷十一", "530-534", "xiazhuang_killed,northern_wei_split", "erzhu_zhao,erzhu_shilong"),
    SourceEntry("weishu_74", "魏书", "卷七十四 尔朱荣传", "魏書/卷七十四", "523-530", "heyin_incident,ge_rong_revolt", "erzhurong,ge_rong,yuan_tianmu"),
    SourceEntry("weishu_75", "魏书", "卷七十五 尔朱兆等传", "魏書/卷七十五", "530-533", "post_mingguang_power_struggle", "erzhu_zhao,erzhu_shilong,erzhu_tianguang"),
    SourceEntry("weishu_80", "魏书", "卷八十 朱瑞等传", "魏書/卷八十", "528-534", "northern_wei_split", "heba_sheng,heba_yue"),
    SourceEntry("weishu_93", "魏书", "卷九十三 恩幸传", "魏書/卷九十三", "-", "court_network", "hougang"),
    SourceEntry("weishu_96", "魏书", "卷九十六 僭伪传", "魏書/卷九十六", "523-528", "ge_rong_revolt", "ge_rong"),
    SourceEntry("tongjian_151", "资治通鉴", "卷151 梁纪七", "資治通鑑/卷151", "526-527", "six_garrisons_revolt,ge_rong_revolt", "ge_rong,erzhurong"),
    SourceEntry("tongjian_152", "资治通鉴", "卷152 梁纪八", "資治通鑑/卷152", "528", "heyin_incident", "erzhurong,xiaozhuang,ge_rong"),
    SourceEntry("tongjian_153", "资治通鉴", "卷153 梁纪九", "資治通鑑/卷153", "529", "yuanhao_campaign", "chen_qingzhi,yuan_hao"),
    SourceEntry("tongjian_154", "资治通鉴", "卷154 梁纪十", "資治通鑑/卷154", "530", "mingguang_assassination", "xiaozhuang,erzhurong,erzhu_shilong"),
    SourceEntry("tongjian_155", "资治通鉴", "卷155 梁纪十一", "資治通鑑/卷155", "531-532", "hanling_battle,gaohuan_uprising", "gaohuan,erzhu_zhao"),
    SourceEntry("tongjian_156", "资治通鉴", "卷156 梁纪十二", "資治通鑑/卷156", "533-534", "northern_wei_split", "gaohuan,yuwentai"),
    SourceEntry("beiqishu_1", "北齐书", "卷一 神武帝上", "北齊書/卷一", "496-532", "gaohuan_uprising", "gaohuan"),
    SourceEntry("beiqishu_2", "北齐书", "卷二 神武帝下", "北齊書/卷二", "532-547", "hanling_battle", "gaohuan"),
    SourceEntry("beishi_5", "北史", "卷五 魏本纪第五", "北史/卷五", "528-531", "heyin_incident,xiazhuang_killed", "xiaozhuang,erzhurong"),
    SourceEntry("beishi_6", "北史", "卷六 齐本纪上", "北史/卷六", "531-534", "gaohuan_uprising,northern_wei_split", "gaohuan"),
    SourceEntry("beishi_48", "北史", "卷四十八 列传第三十六", "北史/卷四十八", "523-533", "heyin_incident,hanling_battle", "erzhurong,erzhu_zhao,erzhu_shilong"),
    SourceEntry("luoyang_1", "洛阳伽蓝记", "卷一 城内", "洛陽伽藍記/卷一", "528-534", "heyin_incident,luoyang_politics", "erzhurong,xiaozhuang"),
    SourceEntry("luoyang_4", "洛阳伽蓝记", "卷四 城西", "洛陽伽藍記/卷四", "530-534", "mingguang_assassination_context", "xiaozhuang"),
]


def ws_export_url(page: str) -> str:
    return f"https://ws-export.wmcloud.org/?lang=zh&format=txt&page={page}"


def ensure_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            work TEXT NOT NULL,
            chapter TEXT NOT NULL,
            page TEXT NOT NULL,
            year_range TEXT,
            event_tags TEXT,
            person_tags TEXT,
            remote_url TEXT NOT NULL,
            local_path TEXT,
            status TEXT NOT NULL,
            content_sha256 TEXT,
            content_length INTEGER,
            fetched_at TEXT
        )
        """
    )
    conn.commit()


def upsert_status(
    conn: sqlite3.Connection,
    entry: SourceEntry,
    remote_url: str,
    local_path: str | None,
    status: str,
    content_sha256: str | None,
    content_length: int | None,
) -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO sources (
            source_id, work, chapter, page, year_range, event_tags, person_tags,
            remote_url, local_path, status, content_sha256, content_length, fetched_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            work=excluded.work,
            chapter=excluded.chapter,
            page=excluded.page,
            year_range=excluded.year_range,
            event_tags=excluded.event_tags,
            person_tags=excluded.person_tags,
            remote_url=excluded.remote_url,
            local_path=excluded.local_path,
            status=excluded.status,
            content_sha256=excluded.content_sha256,
            content_length=excluded.content_length,
            fetched_at=excluded.fetched_at
        """,
        (
            entry.source_id,
            entry.work,
            entry.chapter,
            entry.page,
            entry.year_range,
            entry.event_tags,
            entry.person_tags,
            remote_url,
            local_path,
            status,
            content_sha256,
            content_length,
            fetched_at,
        ),
    )
    conn.commit()


def fetch_text(client: httpx.Client, url: str) -> str:
    resp = client.get(url)
    resp.raise_for_status()
    return resp.text


def save_text(entry: SourceEntry, text: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{entry.source_id}.txt"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def run(limit: int | None = None) -> tuple[int, int]:
    selected = SOURCES if limit is None else SOURCES[:limit]
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_db(conn)

    ok = 0
    fail = 0
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for entry in selected:
            remote = ws_export_url(entry.page)
            try:
                text = fetch_text(client, remote)
                if len(text.strip()) < 200:
                    raise ValueError("exported text too short")
                path = save_text(entry, text)
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                upsert_status(
                    conn,
                    entry,
                    remote,
                    str(path),
                    "downloaded",
                    digest,
                    len(text),
                )
                ok += 1
                print(f"[OK] {entry.source_id} -> {path}")
            except Exception as exc:  # noqa: BLE001
                upsert_status(conn, entry, remote, None, f"failed: {exc}", None, None)
                fail += 1
                print(f"[FAIL] {entry.source_id} -> {exc}")

    conn.close()
    return ok, fail


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Northern Wei sources and index into sqlite database.")
    parser.add_argument("--limit", type=int, default=None, help="Only process first N sources")
    args = parser.parse_args()

    ok, fail = run(limit=args.limit)
    print(f"done: ok={ok}, fail={fail}, db={DB_PATH}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
