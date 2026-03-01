"""Continue outline generation - vol 1 ch22-80 + other volumes."""
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

async def continue_design():
    await session.init('qiewei_v2')
    storage = NovelStorage()
    novel_dir = storage._novel_dir('qiewei_v2')

    # 读取已有大纲
    with open(novel_dir / 'outline' / 'full_outline_raw.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    stripped = raw_data.get('stripped', '')
    try:
        base_outline = json.loads(stripped)
        print(f"已加载基础大纲：{base_outline.get('title')}")
        print(f"卷数：{len(base_outline.get('volumes', []))}")
        existing_chapters = len(base_outline.get('volume1_chapters', []))
        print(f"第一卷已有章节：{existing_chapters}")
    except:
        base_outline = {}
        existing_chapters = 0

    # ========== 续写第一卷 22-80 章 ==========
    if existing_chapters < 80:
        print(f"\n续写第一卷第{existing_chapters+1}-80 章...")

        continuation_prompt = f"""
继续《窃魏》第一卷细纲（第{existing_chapters+1}-80 章），北魏末年穿越爽文。

前{existing_chapters}章已写：李曜穿越→除虎→救公主→赴晋阳→客舍风波

【后续剧情要点】
- Ch22-30：投军尔朱荣，展露军事才能，训练新军
- Ch31-45：随军平叛，火药首秀，升为军司马
- Ch46-60：河阴之变前夕，暗中布局，救下关键大臣
- Ch61-80：河阴之变爆发，主角趁乱收编人马，获封将军

每章：标题 +50 字摘要 + 涉及角色 + 情绪弧线

JSON 格式（只返回章节数组）：
[
  {{"chapter_number": 22, "title": "", "summary": "", "involved_characters": [], "emotional_arc": {{"start": "", "peak": "", "end": ""}}}},
  ...
]
"""

        result = await session._plot_designer.process(
            AgentInput(task_type='outline_design', instruction=continuation_prompt)
        )

        print(f"Raw success: {result.success}")
        print(f"Content len: {len(result.content) if result.content else 0}")

        if result.content:
            # 保存原始内容
            storage._save_json(novel_dir / 'outline' / 'vol1_continuation_raw.json',
                             {"raw": result.content})

            # 尝试解析
            content = result.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                continuation = json.loads(content)
                storage._save_json(novel_dir / 'outline' / 'vol1_continuation.json', continuation)
                print(f"续写成功！新增{len(continuation)}章")

                # 合并
                if 'volume1_chapters' not in base_outline:
                    base_outline['volume1_chapters'] = []
                base_outline['volume1_chapters'].extend(continuation)
                storage._save_json(novel_dir / 'outline' / 'full_outline_merged.json', base_outline)
                print(f"合并后第一卷共{len(base_outline['volume1_chapters'])}章")
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败：{e}，检查 vol1_continuation_raw.json")

    # ========== 生成第二卷细纲 ==========
    print("\n生成第二卷细纲（81-160 章）...")
    vol2_prompt = """
设计《窃魏》第二卷细纲（81-160 章），北魏末年穿越爽文。

【第一卷结尾】李曜在河阴之变中获封将军，初步立足

【第二卷主线】随尔朱荣平定葛荣起义，建立神机营，山东开府

【关键剧情】
- 葛荣大军压境，尔朱荣命李曜为先锋
- 李曜组建神机营（火药部队），训练新军
- 邺城之战，火药破城，一战成名
- 获封山东太守，开府建牙，收服第一批文臣武将
- 迎娶元玉奴（平城公主），政治联姻

每章：标题 +50 字摘要 + 涉及角色 + 情绪弧线

JSON 格式（按 chapter_number 81-160 顺序返回数组）：
[{{"chapter_number": 81, "title": "", "summary": "", "involved_characters": [], "emotional_arc": {{"start": "", "peak": "", "end": ""}}}}, ...]
"""

    result2 = await session._plot_designer.process(
        AgentInput(task_type='outline_design', instruction=vol2_prompt)
    )

    print(f"Vol2 Raw success: {result2.success}")
    if result2.content:
        storage._save_json(novel_dir / 'outline' / 'vol2_raw.json', {"raw": result2.content})
        print(f"Vol2 已保存原始内容 ({len(result2.content)} chars)")

    # ========== 生成第三卷细纲 ==========
    print("\n生成第三卷细纲（161-240 章）...")
    vol3_prompt = """
设计《窃魏》第三卷细纲（161-240 章），北魏末年穿越爽文。

【第二卷结尾】李曜任山东太守，建立初步势力

【第三卷主线】孝庄帝诛尔朱荣，主角收编尔朱残部，占据河北

【关键剧情】
- 孝庄帝暗中联络李曜，欲共诛尔朱荣
- 李曜表面中立，暗中观望
- 尔朱荣被杀，尔朱兆反攻洛阳
- 李曜趁乱收编尔朱残部，实力大增
- 与高欢结盟，共抗尔朱氏
- 河北诸郡望风归附

每章：标题 +50 字摘要 + 涉及角色 + 情绪弧线
JSON 数组格式返回，格式：[{{"chapter_number": 161, ... }}]
"""

    result3 = await session._plot_designer.process(
        AgentInput(task_type='outline_design', instruction=vol3_prompt)
    )

    print(f"Vol3 Raw success: {result3.success}")
    if result3.content:
        storage._save_json(novel_dir / 'outline' / 'vol3_raw.json', {"raw": result3.content})
        print(f"Vol3 已保存原始内容 ({len(result3.content)} chars)")

    print("\n" + "="*60)
    print("大纲生成完成！")
    print("检查目录：data/novels/qiewei_v2/outline/")
    print("="*60)

asyncio.run(continue_design())
