"""
大纲重塑工具 - Director 模式核心功能

使用 LLM 生成深度大纲，包含：
- 多视角结构
- 世界线展开
- 伏笔网络
- 节奏曲线
- 角色弧线
"""

import asyncio
import json
from pathlib import Path
from typing import Any


async def reshape_outline(
    novel_id: str,
    start_chapter: int,
    end_chapter: int,
    output_file: str | None = None,
) -> list[dict]:
    """
    重塑大纲（第 X 章到第 Y 章）

    Args:
        novel_id: 小说 ID
        start_chapter: 起始章节
        end_chapter: 结束章节
        output_file: 输出文件路径

    Returns:
        新生成的章节大纲列表
    """
    from src.skills.director_mode import director_mode

    # 激活 Director 模式
    print(f'=== 激活 Director 模式：{novel_id} ===')
    report = await director_mode.activate(novel_id)

    print(f'已写章节：{report.written_chapters}')
    print(f'当前大纲章节数：{report.outline_chapters}')
    print()

    # 加载现有大纲
    outline_file = Path(f'data/novels/{novel_id}/outline.json')
    if not outline_file.exists():
        raise FileNotFoundError(f'大纲文件不存在：{outline_file}')

    with open(outline_file, 'r', encoding='utf-8') as f:
        outline_data = json.load(f)

    # 找到第一卷
    volume = outline_data['volumes'][0]
    existing_chapters = {ch['chapter_number']: ch for ch in volume['chapters']}

    # 生成新大纲
    print(f'=== 重塑大纲：第{start_chapter}章 - 第{end_chapter}章 ===')
    print()

    new_chapters = []

    for ch_num in range(start_chapter, end_chapter + 1):
        print(f'--- 生成第{ch_num}章大纲 ---')

        # 检查是否已有大纲
        if ch_num in existing_chapters:
            existing = existing_chapters[ch_num]
            print(f'  现有标题：{existing.get("title", "N/A")}')
            print(f'  现有摘要：{existing.get("summary", "")[:50]}...')

        # 使用 Director 模式生成深度大纲
        brief = await director_mode.generate_writing_brief(ch_num)

        chapter_outline = {
            "chapter_id": f"v1_ch{ch_num:02d}",
            "chapter_number": ch_num,
            "title": f"第{ch_num}章标题（待生成）",
            "summary": brief.chapter_outline,
            "key_scenes": [
                {"scene_id": f"s{ch_num}_{i+1}", "description": scene}
                for i, scene in enumerate(brief.scenes)
            ],
            "involved_characters": [c["name"] for c in brief.characters],
            "historical_events": [],
            "emotional_arc": {
                "start": "待生成",
                "peak": "待生成",
                "end": brief.closing_hook,
            },
            "requires_debate": False,
            "debate_config": None,
            # Director 模式新增字段
            "pov_structure": brief.pov_structure,
            "world_context": brief.world_context,
            "target_tension": brief.target_tension,
            "foreshadowing": {
                "plant": brief.foreshadowing_plant,
                "payoff": brief.foreshadowing_payoff,
            },
            "opening_style": brief.opening_style,
            "paragraph_plan": brief.paragraph_plan,
        }

        new_chapters.append(chapter_outline)
        print(f'  开头方式：{brief.opening_style}')
        print(f'  目标紧张度：{brief.target_tension}/10')
        print(f'  多视角：{[p["pov"] for p in brief.pov_structure]}')
        print(f'  世界线：{brief.world_context[:50]}...')
        print()

    # 更新大纲数据
    # 移除旧章节（如果存在）
    volume['chapters'] = [
        ch for ch in volume['chapters']
        if ch['chapter_number'] < start_chapter or ch['chapter_number'] > end_chapter
    ]

    # 添加新章节
    volume['chapters'].extend(new_chapters)
    volume['chapters'].sort(key=lambda x: x['chapter_number'])

    # 保存
    if output_file is None:
        output_file = outline_file

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(outline_data, f, ensure_ascii=False, indent=2)

    print(f'=== 大纲已保存到：{output_file} ===')
    print(f'总章节数：{len(volume["chapters"])}')

    return new_chapters


if __name__ == '__main__':
    # 重塑第 13-20 章大纲
    chapters = asyncio.run(reshape_outline('qiewei_v2', 13, 20))
    print(f'\n生成大纲章节数：{len(chapters)}')
