#!/usr/bin/env python3
"""
《窃魏》小说创作流程 - 继续生成大纲和第一章
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

NOVEL_ID = "qiewei_001"
NOVEL_DIR = Path(f"data/novels/{NOVEL_ID}")


async def call_deepseek(
    system_prompt: str, user_prompt: str, max_tokens: int = 2000
) -> str:
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


async def phase_2_outline_design():
    """Phase 2: 设计大纲"""
    print("=" * 60)
    print("Phase 2: Outline Design")
    print("=" * 60)

    # 读取世界观
    world_setting_file = NOVEL_DIR / "world_setting.json"
    world_setting = world_setting_file.read_text(encoding="utf-8")

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
{world_setting[:1500]}...

要求：
1. 全书分三幕，每幕10章
2. 每章明确标注：核心爽点、历史事件、收服人物
3. 第一章设计：主角穿越、结识尔朱荣、展示价值（火药/战术）
4. 河阴之变安排在第15章左右（全书中间，高潮点）
5. 最终章设计：主角成功建立影子政权，高欢成为明面上的傀儡

输出格式：结构化JSON，包含title, total_chapters, volumes数组。

请输出完整的JSON格式大纲。"""

    print("Generating outline...")
    response = await call_deepseek(system_prompt, user_prompt, max_tokens=4000)

    outline_file = NOVEL_DIR / "outline.json"
    outline_file.write_text(response, encoding="utf-8")

    print("[OK] Outline generated and saved")
    print(f"File: {outline_file}")
    print(f"Length: {len(response)} characters")

    return response


async def phase_3_write_chapter1():
    """Phase 3: 写第一章"""
    print("\n" + "=" * 60)
    print("Phase 3: Chapter 1 Writing")
    print("=" * 60)

    # 读取世界观和大纲
    world_setting_file = NOVEL_DIR / "world_setting.json"
    world_setting = world_setting_file.read_text(encoding="utf-8")

    system_prompt = """你是一位擅长历史权谋小说的专业作家，尤其精通魏晋南北朝时期。

你的写作风格：
1. 画面感优先: 每个场景必须包含光影、色彩、微表情、动作细节
2. 对话有潜台词: 表面说的 vs 实际想的
3. 节奏控制: 紧张场景短句、内心独白长句
4. 半文半白: 对话符合人物身份，文人雅士可带文言，武人平民用白话
5. 爽点前置: 每章必须有至少一个让读者爽的桥段

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
{world_setting[:1200]}...

第一章要求：
1. 标题：《雪夜归人》
2. 场景：孝昌三年冬，秀容川，雪夜
3. 主角穿越后醒来，发现自己在一个陌生帐篷，穿着北魏军服
4. 被当作尔朱荣军队的逃兵/奸细抓住
5. 第一次见尔朱荣：展示军事素养（观察营地布防、指出漏洞）引起注意
6. 展示第一个技能：制作简易火药（用于信号/威慑）
7. 结尾：被尔朱荣暂时收留，但身份存疑，有监视

关键人物设定：
- 主角（幽狼）：现代特种兵，冷静、观察力强、不卑不亢
- 尔朱荣：威严、多疑、爱才、有枭雄气质
- 尔朱兆：尔朱荣侄子，鲁莽、尚武、对主角有敌意

写作要点：
- 主角内心活动要体现现代思维（分析局势、判断危险）
- 环境描写：寒冷、荒凉、军事化的秀容川
- 爽点：主角用现代军事知识在尔朱荣面前成功展示价值
- 对话要有古风但不能太文绉绉

请用Markdown格式输出，章节标题用#，场景分隔用---，字数3500-4500字。"""

    print("Writing Chapter 1...")
    response = await call_deepseek(system_prompt, user_prompt, max_tokens=4000)

    chapter_file = NOVEL_DIR / "chapters/ch_001.md"
    chapter_file.write_text(response, encoding="utf-8")

    print("[OK] Chapter 1 created!")
    print(f"File: {chapter_file}")
    print(f"Length: {len(response)} characters")

    return response


async def main():
    print("\n" + "=" * 60)
    print("《窃魏》Novel Creation - Continue")
    print(f"Project ID: {NOVEL_ID}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        # Phase 2: 大纲
        outline = await phase_2_outline_design()

        # Phase 3: 第一章
        chapter1 = await phase_3_write_chapter1()

        print("\n" + "=" * 60)
        print("*** Creation Complete! ***")
        print("=" * 60)
        print(f"\nProject: {NOVEL_DIR.absolute()}")
        print("\nGenerated files:")
        print("  - world_setting.json (already existed)")
        print("  - outline.json")
        print("  - chapters/ch_001.md")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
