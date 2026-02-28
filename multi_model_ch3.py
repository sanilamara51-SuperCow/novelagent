#!/usr/bin/env python3
"""
《窃魏》第三章 - 多模型协作写作
DeepSeek + 豆包 + Kimi K2 协同创作
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# 初始化三个模型客户端

# 1. DeepSeek - 已有
client_deepseek = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

# 2. 豆包 (字节火山引擎)
# doubao-seed-1-8-251228
client_doubao = AsyncOpenAI(
    api_key="257cc276-9d75-47d3-bae2-80301418b833",
    base_url="https://ark.cn-beijing.volces.com/api/v3",  # 火山引擎北京节点
)

# 3. Kimi K2 Thinking (火山引擎托管)
# kimi-k2-thinking-251104
client_kimi = AsyncOpenAI(
    api_key="257cc276-9d75-47d3-bae2-80301418b833",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

NOVEL_DIR = Path("data/novels/qiewei_001")


async def call_doubao(prompt: str, max_tokens: int = 2000) -> str:
    """调用豆包模型 - 负责情感/细节描写"""
    try:
        response = await client_doubao.chat.completions.create(
            model="doubao-seed-1-8-251228",  # 豆包模型ID
            messages=[
                {
                    "role": "system",
                    "content": "你是一位擅长写古代言情和细腻情感描写的作家。请用优美的文笔描写人物情感、环境细节、心理活动。避免使用破折号，多用短句和具体细节。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.8,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"豆包API错误: {e}")
        return ""


async def call_kimi(prompt: str, max_tokens: int = 2000) -> str:
    """调用Kimi K2模型 - 负责对话/口语化"""
    try:
        response = await client_kimi.chat.completions.create(
            model="kimi-k2-thinking-251104",  # Kimi K2模型ID
            messages=[
                {
                    "role": "system",
                    "content": "你是一位擅长写古代历史小说的作家，精通人物对话。请写口语化、接地气的对话，角色要有口头禅和个性。避免书面语，多用短句、停顿、重复。不要解释，直接写对话。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Kimi API错误: {e}")
        return ""


async def call_deepseek(prompt: str, max_tokens: int = 2000) -> str:
    """调用DeepSeek - 负责骨架/战略"""
    try:
        response = await client_deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位精通北魏史的历史学家和军事 strategist。请设计合理的剧情走向、军事部署、政治博弈。注重逻辑性和历史准确性。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek API错误: {e}")
        return ""


async def generate_chapter_3():
    """生成第三章 - 多模型协作"""
    print("=" * 60)
    print("《窃魏》第三章 - 多模型协作创作")
    print("=" * 60)

    # 先读取前两章的关键信息
    ch1 = (NOVEL_DIR / "chapters/ch_001.md").read_text(encoding="utf-8")
    ch2 = (NOVEL_DIR / "chapters/ch_002.md").read_text(encoding="utf-8")

    print("\n[Step 1] DeepSeek设计第三章骨架...")

    prompt_skeleton = f"""基于《窃魏》前两章，设计第三章的详细大纲：

前文概要：
- 主角魏渊穿越到北魏末年，秀容川
- 展示火药技术，获得尔朱荣初步认可
- 收服赵铁柱、清风，建立小团队
- 雪原伏击马贼大胜，收侯景尊重
- 李娥姿姐妹加入阵营

第三章要求：
标题：《洛阳来使》
核心冲突：尔朱兆嫉妒 + 阴世师试探
关键人物：
- 尔朱兆：尔朱荣侄子，嫉妒主角
- 阴世师：洛阳胡太后使者，士族代表，来看"火药奇才"
- 钱小乙：本章新出场，流民孤儿，被主角收为情报网雏形

情节设计：
1. 尔朱兆回营，得知主角擅自出战大胜，心中嫉恨
2. 阴世师抵达，表面客气，实则试探
3. 阴世师要求看"天雷"演示，暗中设局想抓把柄
4. 主角识破，用改良火药反将一军
5. 钱小乙出场：小偷小摸的流民少年，被主角抓住后收服
6. 尔朱荣观察这一切，对主角更欣赏，但也更警惕

输出格式：
- 场景列表（每个场景的时间、地点、人物、核心冲突）
- 对话要点（每段对话的目的）
- 爽点设计（打脸、收人、展示才能）
- 结尾钩子（引出下一章）

请输出详细的大纲设计。"""

    skeleton = await call_deepseek(prompt_skeleton, max_tokens=2500)
    print("✓ 骨架设计完成")
    print(skeleton[:800] + "...\n")

    # Step 2: Kimi写对话
    print("[Step 2] Kimi写口语化对话...")

    prompt_dialogue = f"""根据以下场景，写三段口语化对话：

场景：阴世师（洛阳来的傲慢士族）在宴会上试探魏渊（穿越者，会造火药）

要求：
1. 阴世师要傲慢、文绉绉但带刺，用士族口吻
2. 魏渊要不卑不亢，有现代思维
3. 尔朱兆要在旁边煽风点火
4. 对话要真实，有停顿、有留白、有潜台词
5. 不要解释，直接写对话

写三段：
1. 阴世师开场试探
2. 关于"天雷是否是妖术"的交锋
3. 魏渊反击，让阴世师下不来台

请输出纯对话内容。"""

    dialogues = await call_kimi(prompt_dialogue, max_tokens=1500)
    print("✓ 对话生成完成")
    print(dialogues[:600] + "...\n")

    # Step 3: 豆包写情感细节
    print("[Step 3] 豆包写情感细腻描写...")

    prompt_emotion = f"""写一段细腻的情感描写：

场景：夜晚，李娥姿在帐中给魏渊缝补战袍（白天马贼战撕破的）

要求：
1. 突出李娥姿的心理活动：感激、好奇、朦胧情愫
2. 环境描写：油灯、毡帐、雪夜、针线的细节
3. 魏渊的心理：现代人的孤独、对未来的思量
4. 氛围要温馨但带一丝忧伤（乱世中的片刻宁静）
5. 不要用破折号，多用短句
6. 不要解释"这意味着什么"，直接写感受

字数：800字左右
请输出这段描写。"""

    emotion = await call_doubao(prompt_emotion, max_tokens=1500)
    print("✓ 情感描写完成")
    print(emotion[:600] + "...\n")

    # Step 4: DeepSeek写钱小乙出场
    print("[Step 4] DeepSeek设计钱小乙出场...")

    prompt_character = f"""设计钱小乙的出场场景：

人物设定：
- 钱小乙：十四岁，流民孤儿，小偷小摸为生
- 性格：机灵、狡黠、爱财但本性不坏
- 被主角抓住偷窃，但反而被收服
- 成为主角情报网的第一个成员

场景：深夜，主角发现有人潜入帐中偷火药配方
经过：
1. 主角装睡，观察小偷手法
2. 小偷（钱小乙）技术娴熟，但太嫩
3. 主角突然发难，制住钱小乙
4. 对话：钱小乙从惊慌到机灵应对
5. 主角看中他的天赋，收服他
6. 钱小乙从此死心塌地

要求：
- 动作描写要专业（小偷的技术细节）
- 对话要生动，钱小乙要有特色
- 转折点要自然

请输出这个场景的详细设计。"""

    xiaoYi_scene = await call_deepseek(prompt_character, max_tokens=1500)
    print("✓ 钱小乙场景完成")
    print(xiaoYi_scene[:600] + "...\n")

    # 保存各部分
    draft_dir = NOVEL_DIR / "drafts"
    draft_dir.mkdir(exist_ok=True)

    (draft_dir / "ch3_skeleton.txt").write_text(skeleton, encoding="utf-8")
    (draft_dir / "ch3_dialogues.txt").write_text(dialogues, encoding="utf-8")
    (draft_dir / "ch3_emotion.txt").write_text(emotion, encoding="utf-8")
    (draft_dir / "ch3_xiaoyi.txt").write_text(xiaoYi_scene, encoding="utf-8")

    print("=" * 60)
    print("✓ 多模型协作完成！")
    print("=" * 60)
    print("\n生成文件：")
    print("  - drafts/ch3_skeleton.txt (DeepSeek：骨架)")
    print("  - drafts/ch3_dialogues.txt (Kimi：对话)")
    print("  - drafts/ch3_emotion.txt (豆包：情感)")
    print("  - drafts/ch3_xiaoyi.txt (DeepSeek：钱小乙)")
    print("\n下一步：人工整合这些素材，写成完整章节")

    return skeleton, dialogues, emotion, xiaoYi_scene


async def main():
    try:
        await generate_chapter_3()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
