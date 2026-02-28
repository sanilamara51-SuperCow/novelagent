#!/usr/bin/env python3
"""
《窃魏》扩写大纲 - 从30章扩展到120章
保持三幕结构，但每幕扩展为40章，共3卷
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

NOVEL_DIR = Path("data/novels/qiewei_001")


async def call_deepseek(
    system_prompt: str, user_prompt: str, max_tokens: int = 4000
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


async def expand_outline():
    """扩写大纲到120章"""
    print("=" * 60)
    print("扩写《窃魏》大纲至120章")
    print("=" * 60)

    # 读取现有世界观和简化大纲
    world_setting_file = NOVEL_DIR / "world_setting.json"
    world_setting = world_setting_file.read_text(encoding="utf-8")

    system_prompt = """你是一位资深历史小说编辑，擅长设计超长篇网文大纲。

《窃魏》需要扩写至120章，分三卷：

**第一卷：秀容风云（第1-40章）**
时间：527-528年（河阴之变前）
主线：穿越、依附尔朱、建立根基、南下洛阳
关键事件：
- 结识尔朱荣，展示价值（火药、练兵）
- 收服第一批班底（斛律金、刘贵等）
- 参与平定葛荣，崭露头角
- 谋划河阴之变

**第二卷：河阴血（第41-80章）**
时间：528-530年（河阴之变到尔朱荣死）
主线：掌控朝廷、建立影子内阁、与孝庄帝博弈
关键事件：
- 河阴之变（第45章左右），控制屠杀名单
- 立孝庄帝，成为皇帝与尔朱荣间的纽带
- 建立晋阳幕府，实际掌控军政
- 收服高欢、宇文泰等人
- 尔朱荣之死（第78-80章），主角接手部分势力

**第三卷：窃魏（第81-120章）**
时间：531-534年（尔朱荣死后到东西魏分裂）
主线：与高欢争雄、建立霸府、最终挟天子令诸侯
关键事件：
- 尔朱氏内乱，主角趁机扩张
- 韩陵之战（第95章左右），与高欢决战
- 控制关中/河北，成为最大军阀
- 立傀儡皇帝，建立影子王朝
- 高欢、宇文泰分别建立东西魏（第120章结局）

每卷40章，每章要求：
- 标题（4-6字，有古风）
- 核心爽点（什么让读者爽）
- 情绪弧线
- 收服/出场人物
- 字数预估（每章4000-5000字）

卷结构：
- 每卷分4个单元，每单元10章
- 单元结尾有小高潮
- 卷结尾有大高潮"""

    user_prompt = f"""基于以下世界观，设计《窃魏》120章详细大纲：

世界观：
{world_setting[:2000]}...

要求：
1. 三卷结构，每卷40章，共120章
2. 第一卷时间：527年冬-528年秋（穿越到河阴前）
3. 第二卷时间：528年秋-530年冬（河阴到尔朱荣死）
4. 第三卷时间：531-534年（最终霸业）
5. 每章包含：标题、爽点、情绪弧线、人物、历史关联
6. 标注关键战役、政治博弈、收服名将的具体章节
7. 女主/感情线穿插安排（至少3位有历史原型的女性角色）

输出JSON格式：
{{
  "title": "窃魏",
  "total_chapters": 120,
  "volumes": [
    {{
      "volume_number": 1,
      "title": "第一卷：秀容风云",
      "subtitle": "借鸡生蛋，依附尔朱",
      "time_range": "527-528",
      "units": [
        {{
          "unit_number": 1,
          "title": "第一单元：雪夜惊雷",
          "chapters": [
            {{
              "chapter_id": "ch_001",
              "chapter_number": 1,
              "title": "章节标题",
              "summary": "概要",
              "thrill_point": "爽点",
              "emotion_arc": "情绪弧线",
              "characters": ["出场人物"],
              "historical_event": "历史事件关联"
            }}
          ]
        }}
      ]
    }}
  ]
}}

请生成完整的120章大纲。"""

    print("正在生成120章大纲...")
    response = await call_deepseek(system_prompt, user_prompt, max_tokens=4000)

    # 保存
    outline_file = NOVEL_DIR / "outline_expanded.json"
    outline_file.write_text(response, encoding="utf-8")

    print("[OK] 扩写大纲已生成")
    print(f"文件: {outline_file}")
    print(f"长度: {len(response)} 字符")

    # 显示前几章
    print("\n大纲预览（前10章）：")
    print("-" * 60)
    print(response[:2000])
    print("...")

    return response


async def main():
    print("\n《窃魏》大纲扩写系统")
    print("=" * 60)

    try:
        await expand_outline()
        print("\n" + "=" * 60)
        print("扩写完成！")
        print("=" * 60)
        print(f"\n项目位置: {NOVEL_DIR}")
        print("文件: outline_expanded.json (120章)")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
