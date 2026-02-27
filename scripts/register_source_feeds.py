from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


DB_PATH = Path("data/knowledge_base/source_catalog.db")


@dataclass(frozen=True)
class Feed:
    feed_id: str
    title: str
    url: str
    kind: str
    format_hint: str
    reliability: str
    notes: str


FEEDS: list[Feed] = [
    Feed("ctext_weishu_work", "ctext 魏書（全书）", "https://ctext.org/wiki.pl?if=gb&res=801592", "portal", "html/wiki", "high", "官方学术站点"),
    Feed("ctext_beishi_work", "ctext 北史（全书）", "https://ctext.org/wiki.pl?if=gb&res=216850", "portal", "html/wiki", "high", "官方学术站点"),
    Feed("ctext_beiqishu_work", "ctext 北齊書（全书）", "https://ctext.org/wiki.pl?if=gb&res=593209", "portal", "html/wiki", "high", "官方学术站点"),
    Feed("ctext_zztj_work", "ctext 資治通鑑（全书）", "https://ctext.org/wiki.pl?if=gb&res=638056", "portal", "html/wiki", "high", "官方学术站点"),
    Feed("ctext_luoyang_work", "ctext 洛陽伽藍記（全书）", "https://ctext.org/wiki.pl?if=gb&res=751279", "portal", "html/wiki", "high", "官方学术站点"),
    Feed("ctext_weishu_10", "ctext 魏書 帝紀第十 孝莊紀", "https://ctext.org/wiki.pl?chapter=498927&if=gb", "chapter", "html", "high", "主线核心"),
    Feed("ctext_weishu_74", "ctext 魏書 列傳第六十二 爾朱榮", "https://ctext.org/wiki.pl?if=gb&chapter=598331", "chapter", "html", "high", "主线核心"),
    Feed("ctext_beishi_5", "ctext 北史 卷五 魏本紀第五", "https://ctext.org/wiki.pl?chapter=809514&if=gb", "chapter", "html", "high", "主线核心"),
    Feed("ctext_beishi_48", "ctext 北史 卷四十八 列傳第三十六", "https://ctext.org/wiki.pl?chapter=1934881&if=gb", "chapter", "html", "high", "尔朱系统"),
    Feed("ctext_luoyang_1", "ctext 洛陽伽藍記 卷一", "https://ctext.org/wiki.pl?chapter=95718&if=gb", "chapter", "html", "high", "洛阳政治生态"),
    Feed("wikisource_weishu", "维基文库 魏書", "https://zh.wikisource.org/wiki/魏書", "portal", "wiki/export", "high", "可导出，当前环境限流"),
    Feed("wikisource_beishi", "维基文库 北史", "https://zh.wikisource.org/wiki/北史", "portal", "wiki/export", "high", "可导出，当前环境限流"),
    Feed("wikisource_beiqishu", "维基文库 北齊書", "https://zh.wikisource.org/wiki/北齊書", "portal", "wiki/export", "high", "可导出，当前环境限流"),
    Feed("wikisource_zztj", "维基文库 資治通鑑", "https://zh.wikisource.org/wiki/資治通鑑", "portal", "wiki/export", "high", "可导出，当前环境限流"),
    Feed("wikisource_luoyang", "维基文库 洛陽伽藍記", "https://zh.wikisource.org/wiki/洛陽伽藍記", "portal", "wiki/export", "high", "可导出，当前环境限流"),
    Feed("wikisource_zztj_151", "维基文库 資治通鑑/卷151", "https://zh.wikisource.org/wiki/資治通鑑/卷151", "chapter", "wiki", "high", "六镇起义背景"),
    Feed("wikisource_zztj_152", "维基文库 資治通鑑/卷152", "https://zh.wikisource.org/wiki/資治通鑑/卷152", "chapter", "wiki", "high", "河阴之变"),
    Feed("wikisource_zztj_154", "维基文库 資治通鑑/卷154", "https://zh.wikisource.org/wiki/資治通鑑/卷154", "chapter", "wiki", "high", "明光殿刺杀"),
    Feed("wikisource_zztj_155", "维基文库 資治通鑑/卷155", "https://zh.wikisource.org/wiki/資治通鑑/卷155", "chapter", "wiki", "high", "高欢起兵/韩陵"),
    Feed("wikisource_zztj_156", "维基文库 資治通鑑/卷156", "https://zh.wikisource.org/wiki/資治通鑑/卷156", "chapter", "wiki", "high", "北魏分裂前后"),
    Feed("wikisource_weishu_10", "维基文库 魏書/卷十", "https://zh.wikisource.org/wiki/魏書/卷十", "chapter", "wiki", "high", "孝庄纪"),
    Feed("wikisource_weishu_74", "维基文库 魏書/卷七十四", "https://zh.wikisource.org/wiki/魏書/卷七十四", "chapter", "wiki", "high", "尔朱荣传"),
    Feed("wikisource_weishu_75", "维基文库 魏書/卷七十五", "https://zh.wikisource.org/wiki/魏書/卷七十五", "chapter", "wiki", "high", "尔朱兆等"),
    Feed("wikisource_luoyang_1", "维基文库 洛陽伽藍記/卷一", "https://zh.wikisource.org/wiki/洛陽伽藍記/卷一", "chapter", "wiki", "high", "永宁寺/河阴后"),
    Feed("wikisource_luoyang_4", "维基文库 洛陽伽藍記/卷四", "https://zh.wikisource.org/wiki/洛陽伽藍記/卷四", "chapter", "wiki", "high", "宣忠寺语境"),
    Feed("github_24histories", "GitHub Twenty-Four-Histories", "https://github.com/yuanshiming/Twenty-Four-Histories", "github", "tex", "high", "已本地克隆"),
    Feed("github_zztj_jy0284", "GitHub zizhitongjian (JY0284)", "https://github.com/JY0284/zizhitongjian", "github", "markdown", "high", "已本地克隆"),
    Feed("github_26histories", "GitHub 26-histories", "https://github.com/jinyangwang27/26-histories", "github", "markdown", "medium", "适合RAG但需抽检"),
    Feed("github_guoxue_tongjian", "GitHub guoxue-study/tongjian", "https://github.com/guoxue-study/tongjian", "github", "web resources", "medium", "易读版/二次整理"),
    Feed("github_gosaintmrc_zztj", "GitHub gosaintmrc/zztj", "https://github.com/gosaintmrc/zztj", "github", "mixed", "medium", "含译注与拼音"),
    Feed("archive_search_weishu", "Internet Archive 魏书检索", "https://archive.org/search?query=魏书", "archive", "pdf/txt/mixed", "medium", "作兜底镜像"),
    Feed("archive_search_beishi", "Internet Archive 北史检索", "https://archive.org/search?query=北史", "archive", "pdf/txt/mixed", "medium", "作兜底镜像"),
]


def main() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_feeds (
            feed_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            kind TEXT NOT NULL,
            format_hint TEXT,
            reliability TEXT,
            notes TEXT
        )
        """
    )
    for f in FEEDS:
        conn.execute(
            """
            INSERT INTO source_feeds (feed_id, title, url, kind, format_hint, reliability, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(feed_id) DO UPDATE SET
                title=excluded.title,
                url=excluded.url,
                kind=excluded.kind,
                format_hint=excluded.format_hint,
                reliability=excluded.reliability,
                notes=excluded.notes
            """,
            (f.feed_id, f.title, f.url, f.kind, f.format_hint, f.reliability, f.notes),
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM source_feeds").fetchone()[0]
    conn.close()
    print(f"registered_source_feeds={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
