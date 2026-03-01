"""Generate full outline for qiewei_v2 - 500+ chapters."""
import asyncio
import sys
import os
import json

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session
from src.agents.base_agent import AgentInput
from src.utils.persistence import NovelStorage

async def design():
    await session.init('qiewei_v2')

    # 分两步：先生成全书粗纲，再生成第一卷细纲

    # ========== 第一步：全书粗纲 ==========
    print("="*60)
    print("生成全书粗纲（500+ 章，5-6 卷）...")
    print("="*60)

    macro_outline = """
设计《窃魏》500+ 章超长篇大纲，北魏末年穿越爽文，综合型金手指。

【主角】李曜，现代军械工程师 + 军事史研究者，穿越成秀容川猎户。
【金手指】
1. 火药配方（黑火药→颗粒火药→硝化甘油）
2. 现代冶金（土法炼钢、改良灌钢法）
3. 军事组织（参谋部、后勤、训练体系）
4. 历史预知（知道 523-550 年所有大事）
【女主】
1. 元玉奴（平城公主）- 政治联姻，正统性
2. 斛律红玉（敕勒族女将）- 武力担当
3. 崔清漪（清河崔氏嫡女）- 士族纽带
【收服名将】高敖曹、彭乐、斛律光、段韶、杨忠（杨坚之父）、独孤信等

【全书分卷粗纲】
卷一（1-80 章）：秀容川起家，救公主，投尔朱荣，河阴之变布局
卷二（81-160 章）：平定葛荣，建立神机营，山东开府
卷三（161-240 章）：孝庄帝诛尔朱荣，主角收编尔朱残部，占据河北
卷四（241-320 章）：与高欢决战韩陵，火药大破，统一河北
卷五（321-400 章）：逼宫魏帝，禅让称帝，建立新朝（魏/周/汉？）
卷六（401-500+ 章）：南征梁朝，北伐柔然，西并关中，一统天下

请生成：
1. 全书总纲（title, total_chapters, volumes[] 每卷一句话概述）
2. 第一卷详细大纲（1-80 章，每章标题 +50 字摘要 + 涉及角色 + 情绪弧线）

JSON 格式：
{
  "title": "窃魏",
  "total_chapters": 500,
  "main_storyline": "...",
  "volumes": [
    {"volume_number": 1, "title": "...", "chapter_range": [1,80], "summary": "..."},
    {"volume_number": 2, "title": "...", "chapter_range": [81,160], "summary": "..."},
    ...
  ],
  "volume1_chapters": [
    {"chapter_number": 1, "title": "", "summary": "", "involved_characters": [], "emotional_arc": {"start": "", "peak": "", "end": ""}},
    ...
  ]
}
"""

    result = await session._plot_designer.process(
        AgentInput(task_type='outline_design', instruction=macro_outline)
    )

    print(f"Raw success: {result.success}")
    print(f"Content len: {len(result.content) if result.content else 0}")

    # 保存原始内容
    storage = NovelStorage()
    novel_dir = storage._novel_dir('qiewei_v2')

    if result.content:
        # 提取 JSON
        content = result.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # 保存
        data = {"raw_outline": result.content, "stripped": content}
        storage._save_json(novel_dir / 'outline' / 'full_outline_raw.json', data)
        print(f"Saved raw outline: {len(result.content)} chars")

        # 尝试解析
        try:
            outline_data = json.loads(content)
            storage._save_json(novel_dir / 'outline' / 'full_outline.json', outline_data)
            print(f"Saved parsed outline!")
            print(f"  Title: {outline_data.get('title')}")
            print(f"  Total chapters: {outline_data.get('total_chapters')}")
            print(f"  Volumes: {len(outline_data.get('volumes', []))}")
            if outline_data.get('volume1_chapters'):
                print(f"  Volume 1 chapters: {len(outline_data['volume1_chapters'])}")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print("Check full_outline_raw.json for manual fix")
    else:
        print("No content generated!")

asyncio.run(design())
