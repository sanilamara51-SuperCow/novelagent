#!/usr/bin/env python3
"""清洗ctext下载的史料文本"""

import html
import re
from pathlib import Path

RAW_DIR = Path("data/knowledge_base/raw")


def clean_ctext_text(text: str) -> str:
    """清洗ctext.org下载的文本"""
    # 解码HTML实体
    text = html.unescape(text)

    # 去除导航栏内容（ctext的标准导航）
    lines = text.split("\n")
    content_lines = []
    in_content = False

    # ctext正文通常在"原文"或标题之后开始
    for line in lines:
        line = line.strip()

        # 跳过导航链接
        if any(
            skip in line
            for skip in [
                "本站介紹",
                "簡介",
                "字體試驗頁",
                "+協助",
                "+常見問答集",
                "+使用說明",
                "+工具",
                "系統統計",
                "+數位人文",
                "登入",
                "中國哲學書電子化計劃",
                "檢索",
                "書名檢索",
                "简体",
                "English",
                "原典全文",
                "簡介說明",
                "相關資料",
                "字典",
                "討論區",
                "圖書館",
                "維基數據",
                "維基",
                "->",
                "[查看正文]",
                "[修改]",
                "[查看歷史]",
            ]
        ):
            continue

        # 跳过英文翻译（保留中文原文）
        if re.match(r"^[A-Z][a-z].*[a-z]{3,}", line):
            continue

        # 跳过纯数字行
        if re.match(r"^\d+$", line):
            continue

        # 保留中文内容
        if len(line) > 5 and any("\u4e00" <= c <= "\u9fff" for c in line):
            content_lines.append(line)

    return "\n".join(content_lines)


def process_file(filepath: Path) -> None:
    """处理单个文件"""
    text = filepath.read_text(encoding="utf-8")
    cleaned = clean_ctext_text(text)

    # 写回
    filepath.write_text(cleaned, encoding="utf-8")

    print(f"[CLEANED] {filepath.name}: {len(text)} -> {len(cleaned)} chars")


def main():
    # 处理所有.txt文件
    for txt_file in RAW_DIR.glob("*.txt"):
        if txt_file.stat().st_size > 1000:  # 只处理大文件
            process_file(txt_file)

    print("\n清洗完成")


if __name__ == "__main__":
    main()
