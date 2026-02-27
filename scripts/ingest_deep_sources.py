from __future__ import annotations

import argparse
import hashlib
import html
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx


DB_PATH = Path("data/knowledge_base/source_catalog.db")
RAW_ROOT = Path("data/knowledge_base/raw")


@dataclass(frozen=True)
class Doc:
    doc_id: str
    work: str
    chapter: str
    source_kind: str
    source_ref: str
    event_tags: str
    person_tags: str


REMOTE_DOCS = [
    Doc("ctext_weishu_10", "魏书", "帝纪第十 孝庄纪", "ctext", "https://ctext.org/wiki.pl?chapter=498927&if=gb", "heyin_incident,mingguang_assassination", "xiaozhuang,erzhurong"),
    Doc("ctext_weishu_74", "魏书", "列传第六十二 尔朱荣传", "ctext", "https://ctext.org/wiki.pl?if=gb&chapter=598331", "heyin_incident,ge_rong_revolt", "erzhurong,ge_rong,yuan_tianmu"),
    Doc("ctext_beishi_5", "北史", "卷五 魏本纪第五", "ctext", "https://ctext.org/wiki.pl?chapter=809514&if=gb", "heyin_incident,xiazhuang_killed", "xiaozhuang"),
    Doc("ctext_beishi_48", "北史", "卷四十八 列传第三十六", "ctext", "https://ctext.org/wiki.pl?chapter=1934881&if=gb", "heyin_incident,hanling_battle", "erzhurong,erzhu_zhao,erzhu_shilong"),
    Doc("ctext_beiqishu_1", "北齐书", "卷一 神武帝上", "ctext", "https://ctext.org/wiki.pl?chapter=96393&if=gb", "gaohuan_uprising", "gaohuan"),
    Doc("ctext_beiqishu_2", "北齐书", "卷二 神武帝下", "ctext", "https://ctext.org/wiki.pl?if=gb&remap=gb&res=593209", "hanling_battle", "gaohuan"),
    Doc("ctext_luoyang_1", "洛阳伽蓝记", "卷一", "ctext", "https://ctext.org/wiki.pl?chapter=95718&if=gb", "heyin_incident,luoyang_politics", "erzhurong,xiaozhuang"),
    Doc("ctext_luoyang_2", "洛阳伽蓝记", "卷二", "ctext", "https://ctext.org/wiki.pl?chapter=167157&if=gb", "luoyang_politics", "xiazhuang"),
]


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_documents (
            doc_id TEXT PRIMARY KEY,
            work TEXT NOT NULL,
            chapter TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            event_tags TEXT,
            person_tags TEXT,
            content_sha256 TEXT NOT NULL,
            content_length INTEGER NOT NULL,
            ingested_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_texts (
            doc_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES source_documents(doc_id)
        )
        """
    )
    conn.commit()


def upsert_doc(conn: sqlite3.Connection, doc: Doc, text: str) -> None:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ingested_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO source_documents (
            doc_id, work, chapter, source_kind, source_ref, event_tags, person_tags,
            content_sha256, content_length, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET
            work=excluded.work,
            chapter=excluded.chapter,
            source_kind=excluded.source_kind,
            source_ref=excluded.source_ref,
            event_tags=excluded.event_tags,
            person_tags=excluded.person_tags,
            content_sha256=excluded.content_sha256,
            content_length=excluded.content_length,
            ingested_at=excluded.ingested_at
        """,
        (
            doc.doc_id,
            doc.work,
            doc.chapter,
            doc.source_kind,
            doc.source_ref,
            doc.event_tags,
            doc.person_tags,
            digest,
            len(text),
            ingested_at,
        ),
    )
    conn.execute(
        """
        INSERT INTO source_texts (doc_id, content)
        VALUES (?, ?)
        ON CONFLICT(doc_id) DO UPDATE SET content=excluded.content
        """,
        (doc.doc_id, text),
    )
    conn.commit()


def read_text(path: Path) -> str:
    for enc in ("utf-8", "gb18030", "big5"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_html_to_text(raw_html: str) -> str:
    no_script = re.sub(r"<script[\s\S]*?</script>", " ", raw_html, flags=re.IGNORECASE)
    no_style = re.sub(r"<style[\s\S]*?</style>", " ", no_script, flags=re.IGNORECASE)
    no_tags = re.sub(r"<[^>]+>", " ", no_style)
    text = html.unescape(no_tags)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def collect_local_docs() -> list[tuple[Doc, str]]:
    docs: list[tuple[Doc, str]] = []

    local_specs: list[tuple[Path, Doc]] = [
        (
            RAW_ROOT / "twenty_four_histories" / "北齊書" / "卷一帝紀第一神武上.tex",
            Doc("local_beiqishu_1", "北齐书", "卷一 神武帝上", "local_file", "twenty_four_histories/北齊書/卷一帝紀第一神武上.tex", "gaohuan_uprising", "gaohuan"),
        ),
        (
            RAW_ROOT / "twenty_four_histories" / "北齊書" / "卷二帝紀第二神武下.tex",
            Doc("local_beiqishu_2", "北齐书", "卷二 神武帝下", "local_file", "twenty_four_histories/北齊書/卷二帝紀第二神武下.tex", "hanling_battle", "gaohuan"),
        ),
        (
            RAW_ROOT / "twenty_four_histories" / "北史" / "卷五魏本紀第五.tex",
            Doc("local_beishi_5", "北史", "卷五 魏本纪第五", "local_file", "twenty_four_histories/北史/卷五魏本紀第五.tex", "heyin_incident,xiazhuang_killed", "xiaozhuang"),
        ),
        (
            RAW_ROOT / "twenty_four_histories" / "北史" / "卷六齊本紀上第六.tex",
            Doc("local_beishi_6", "北史", "卷六 齐本纪上", "local_file", "twenty_four_histories/北史/卷六齊本紀上第六.tex", "gaohuan_uprising,northern_wei_split", "gaohuan"),
        ),
        (
            RAW_ROOT / "twenty_four_histories" / "北史" / "卷四十八列傳第三十六.tex",
            Doc("local_beishi_48", "北史", "卷四十八 列传第三十六", "local_file", "twenty_four_histories/北史/卷四十八列傳第三十六.tex", "heyin_incident,hanling_battle", "erzhurong,erzhu_zhao,erzhu_shilong"),
        ),
        (
            RAW_ROOT / "twenty_four_histories" / "北史" / "卷四十九列傳第三十七.tex",
            Doc("local_beishi_49", "北史", "卷四十九 列传第三十七", "local_file", "twenty_four_histories/北史/卷四十九列傳第三十七.tex", "northern_wei_split", "heba_yue,yuwentai"),
        ),
    ]

    for n in range(151, 157):
        md_matches = sorted((RAW_ROOT / "zizhitongjian_repo" / "chapters").glob(f"{n}_*.md"))
        if md_matches:
            path = md_matches[0]
            local_specs.append(
                (
                    path,
                    Doc(
                        f"local_tongjian_{n}",
                        "资治通鉴",
                        f"卷{n}",
                        "local_file",
                        str(path.relative_to(RAW_ROOT)).replace("\\", "/"),
                        "six_garrisons_revolt,ge_rong_revolt,heyin_incident,mingguang_assassination,hanling_battle,northern_wei_split",
                        "erzhurong,xiaozhuang,gaohuan,ge_rong,chen_qingzhi,yuan_hao",
                    ),
                )
            )

    local_specs.extend(
        [
            (
                RAW_ROOT / "SOURCE_MAP.md",
                Doc("local_source_map_v1", "索引", "SOURCE_MAP", "local_file", "SOURCE_MAP.md", "all", "all"),
            ),
            (
                RAW_ROOT / "SOURCE_MAP_DEEP_V2.md",
                Doc("local_source_map_v2", "索引", "SOURCE_MAP_DEEP_V2", "local_file", "SOURCE_MAP_DEEP_V2.md", "all", "all"),
            ),
        ]
    )

    for path, doc in local_specs:
        if path.exists():
            docs.append((doc, read_text(path)))

    return docs


def collect_remote_docs() -> list[tuple[Doc, str]]:
    docs: list[tuple[Doc, str]] = []
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for doc in REMOTE_DOCS:
            try:
                resp = client.get(doc.source_ref)
                resp.raise_for_status()
                text = normalize_html_to_text(resp.text)
                if len(text) > 500:
                    docs.append((doc, text))
            except Exception:
                continue
    return docs


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest deeply mined Northern Wei setting sources into sqlite database")
    parser.add_argument("--no-remote", action="store_true", help="Skip remote ctext ingest")
    args = parser.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)

    total = 0
    for doc, text in collect_local_docs():
        upsert_doc(conn, doc, text)
        total += 1
        print(f"[LOCAL] {doc.doc_id} len={len(text)}")

    if not args.no_remote:
        for doc, text in collect_remote_docs():
            upsert_doc(conn, doc, text)
            total += 1
            print(f"[REMOTE] {doc.doc_id} len={len(text)}")

    conn.close()
    print(f"ingested_docs={total} db={DB_PATH}")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
