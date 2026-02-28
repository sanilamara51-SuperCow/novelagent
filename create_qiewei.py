#!/usr/bin/env python3
"""
《窃魏》小说创作流程 - 使用DeepSeek API
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# 初始化DeepSeek客户端
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

# 小说项目目录
NOVEL_ID = "qiewei_001"
NOVEL_DIR = Path(f"data/novels/{NOVEL_ID}")


async def call_deepseek(
    system_prompt: str, user_prompt: str, max_tokens: int = 2000
) -> str:
    """调用DeepSeek API"""
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return response.choices[0].message.content


async def phase_1_world_building():
    """Phase 1: 构建世界观"""
    print("=" * 60)
    print("Phase 1: 世界观构建 (WorldBuilder)")
    print("=" * 60)

    system_prompt = """你是一位精通北魏史的历史学家和世界观设计师。
你的任务是为穿越历史小说《窃魏》构建详细的世界观。

《窃魏》设定：
- 类型：穿越历史（男主角）
- 时期：北魏末年，528-532年
- 主线：现代特种兵穿越到528年，依附尔朱荣势力，参与河阴之变，最终"窃"取北魏政权
- 爽点：军事碾压、政治博弈、收服名将、建立霸业

输出格式：结构化JSON，包含以下字段：
- era: 时期名称
- year_range: [起始年, 结束年]
- political_system: 政治制度描述
- social_structure: 社会结构（鲜卑贵族、汉人士族、流民等）
- geography: {capital: 都城, key_locations: [重要地点]}
- key_events: [{year, event, description, changeable(能否改变)}]
- factions: [{name, leader, stance, strength}]
- notable_figures: [{name, identity, personality, current_position}]
- protagonist: {background, starting_position, advantages, challenges}
- story_hooks: [故事钩子/爽点设计]

注意：
1. key_events中changeable=true表示主角可以改变的事件
2. 设计3-5个核心爽点（军事碾压点、政治博弈点、收服名将点）
3. 主角起始位置要合理（不能太弱也不能太强）"""

    user_prompt = """请为《窃魏》设计完整的世界观：

基本设定：
- 主角：现代特种部队军官，精通格斗、战术、火器原理
- 穿越时间：北魏孝昌三年（527年）冬，六镇起义后
- 穿越地点：秀容川（今山西忻州），尔朱荣势力范围
- 金手指：超级记忆力（过目不忘）+ 基础化学知识（能制作火药、肥皂等）

要求：
1. 设计主角如何结识尔朱荣（要有合理性，不能太突兀）
2. 设计3个核心爽点场景（军事/政治/个人武力）
3. 列出主角可以收服的历史人物（至少5人，说明收服策略）
4. 标注河阴之变（528年）在故事中的作用（可改变/不可改变）
5. 设计最终目标：不是自己做皇帝，而是"挟天子以令诸侯"，建立影子王朝

请输出完整的JSON格式世界观设定。"""

    print("正在生成世界观...")
    response = await call_deepseek(system_prompt, user_prompt, max_tokens=4000)

    # 保存世界观
    world_setting_file = NOVEL_DIR / "world_setting.json"
    world_setting_file.write_text(response, encoding="utf-8")

    print("✓ 世界观已生成并保存")
    print(f"文件位置: {world_setting_file}")
    print("\n" + "=" * 60)
    print(response[:500] + "..." if len(response) > 500 else response)
    print("=" * 60 + "\n")

    return response


async def phase_2_outline_design(world_setting: str):
    """Phase 2: 设计大纲"""
    print("=" * 60)
    print("Phase 2: 大纲设计 (PlotDesigner)")
    print("=" * 60)

    system_prompt = """你是一位资深历史小说编辑和大纲设计师。
你的任务是为《窃魏》设计完整的三幕式大纲。

小说结构要求：
- 第一幕：依附尔朱（第1-10章）- 借鸡生蛋，建立根基
- 第二幕：河阴之变（第11-20章）- 清洗旧势力，建立影子内阁
- 第三幕：高欢接盘（第21-30章）- 暗中操控，建立霸业

每章必须包含：
- 标题（简洁有力）
- 核心爽点（什么让读者爽）
- 历史事件（与史实的结合点）
- 情绪弧线（紧张/轻松/高潮/转折）
- 收服人物（本章收服的历史人物）

爽点设计原则：
1. 军事碾压：现代战术 vs 古代军队
2. 政治博弈：主角用现代政治智慧玩弄古人
3. 收服名将：尔朱兆、高欢、侯景、贺拔岳、宇文泰等
4. 美人计： historically accurate female characters
5. 生死一线：主角多次面临绝境但反杀

注意：
- 河阴之变（528年）必须发生，这是历史的转折点
- 但可以改变：主角提前布局，让清洗更有针对性，保留有用之人
- 最终BOSS不是尔朱荣，而是如何在高欢崛起后保持控制权"""

    user_prompt = f"""基于以下世界观，设计《窃魏》完整30章大纲：

世界观概要：
{world_setting[:1000]}...

要求：
1. 全书分三幕，每幕10章
2. 每章明确标注：核心爽点、历史事件、收服人物
3. 第一章设计：主角穿越、结识尔朱荣、展示价值（火药/战术）
4. 河阴之变安排在第15章左右（全书中间，高潮点）
5. 最终章设计：主角成功建立影子政权，高欢成为明面上的傀儡

输出格式：
{{
  "title": "窃魏",
  "total_chapters": 30,
  "volumes": [
    {{
      "volume_number": 1,
      "title": "第一幕标题",
      "summary": "幕概要",
      "chapters": [
        {{
          "chapter_id": "ch_001",
          "chapter_number": 1,
          "title": "章节标题",
          "summary": "章节概要",
          "key_scene": "核心场景",
          "emotional_arc": "情绪弧线",
          "historical_event": "关联历史事件",
          "recruited_characters": ["收服人物"],
          "thrill_point": "爽点设计"
        }}
      ]
    }}
  ]
}}

请输出完整的JSON格式大纲。"""

    print("正在生成大纲...")
    response = await call_deepseek(system_prompt, user_prompt, max_tokens=4000)

    # 保存大纲
    outline_file = NOVEL_DIR / "outline.json"
    outline_file.write_text(response, encoding="utf-8")

    print("✓ 大纲已生成并保存")
    print(f"文件位置: {outline_file}")
    print("\n" + "=" * 60)
    print(response[:800] + "..." if len(response) > 800 else response)
    print("=" * 60 + "\n")

    return response


async def phase_3_write_chapter1(world_setting: str, outline: str):
    """Phase 3: 写第一章"""
    print("=" * 60)
    print("Phase 3: 第一章创作 (Writer)")
    print("=" * 60)

    system_prompt = """你是一位擅长历史权谋小说的专业作家，尤其精通魏晋南北朝时期。

你的写作风格：
1. **画面感优先**: 每个场景必须包含光影、色彩、微表情、动作细节
2. **对话有潜台词**: 表面说的 vs 实际想的
3. **节奏控制**: 紧张场景短句、内心独白长句
4. **半文半白**: 对话符合人物身份，文人雅士可带文言，武人平民用白话
5. **爽点前置**: 每章必须有至少一个让读者爽的桥段

第一章要求：
- 开篇建立主角形象（现代特种兵，冷静、专业、有领导力）
- 穿越场景要有真实感（不是突然醒来，而是有过程）
- 快速建立与尔朱荣的第一次接触（要有戏剧性）
- 展示第一个金手指：火药/战术/格斗技能
- 结尾留钩子（让读者想看第二章）

禁止：
- 不要现代网络用语
- 不要过多解释穿越原理
- 不要让主角太弱（特种兵设定要有体现）
- 不要让对话太白话（要有古风）"""

    user_prompt = f"""请创作《窃魏》第一章。

世界观设定：
{world_setting[:800]}...

第一章要求：
1. 标题：《雪夜归人》或类似有画面感的标题
2. 场景：孝昌三年冬，秀容川，雪夜
3. 主角穿越后醒来，发现自己在一个陌生帐篷，穿着北魏军服
4. 被当作尔朱荣军队的逃兵/奸细抓住
5. 第一次见尔朱荣：展示军事素养（观察营地布防、指出漏洞）引起注意
6. 展示第一个技能：制作简易火药（用于信号/威慑）
7. 结尾：被尔朱荣暂时收留，但身份存疑，有监视

写作要点：
- 主角内心活动要体现现代思维（分析局势、判断危险）
- 尔朱荣形象：威严、多疑、爱才
- 秀容川环境描写：寒冷、荒凉、军事化
- 爽点：主角用现代军事知识在尔朱荣面前装逼成功

请用Markdown格式输出，章节标题用#，场景分隔用---，字数3000-4000字。"""

    print("正在创作第一章...")
    response = await call_deepseek(system_prompt, user_prompt, max_tokens=4000)

    # 保存章节
    chapter_file = NOVEL_DIR / "chapters/ch_001.md"
    chapter_file.parent.mkdir(parents=True, exist_ok=True)
    chapter_file.write_text(response, encoding="utf-8")

    print("✓ 第一章创作完成！")
    print(f"文件位置: {chapter_file}")
    print(f"字数: {len(response)}")
    print("\n" + "=" * 60)
    print("章节预览（前1500字）：")
    print("-" * 60)
    preview = response[:1500]
    print(preview + "..." if len(response) > 1500 else response)
    print("=" * 60 + "\n")

    return response


async def main():
    """主流程"""
    print("\n" + "=" * 60)
    print("《窃魏》小说创作系统启动")
    print(f"项目ID: {NOVEL_ID}")
    print(f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    # 创建项目目录
    NOVEL_DIR.mkdir(parents=True, exist_ok=True)
    (NOVEL_DIR / "chapters").mkdir(exist_ok=True)
    (NOVEL_DIR / "characters").mkdir(exist_ok=True)

    try:
        # Phase 1: 世界观
        world_setting = await phase_1_world_building()

        # Phase 2: 大纲
        outline = await phase_2_outline_design(world_setting)

        # Phase 3: 第一章
        chapter1 = await phase_3_write_chapter1(world_setting, outline)

        print("\n" + "=" * 60)
        print("✓✓✓ 创作流程完成！✓✓✓")
        print("=" * 60)
        print(f"\n项目文件位置: {NOVEL_DIR.absolute()}")
        print("\n已生成文件:")
        print(f"  - world_setting.json (世界观)")
        print(f"  - outline.json (30章大纲)")
        print(f"  - chapters/ch_001.md (第一章)")
        print("\n下一步:")
        print("  1. 查看并修改世界观/大纲")
        print("  2. 继续创作第二章")
        print("  3. 设置RAG知识库检索史料细节")

    except Exception as e:
        print(f"\n❌ 创作流程出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
