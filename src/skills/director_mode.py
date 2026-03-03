"""
Director Mode - 导演模式超级 Skill

这是 Director（总控规划官）的核心接口。启动后，Claude 作为 Director，
通过 LLM 大脑进行战前分析，生成 WritingBrief，指挥 Pipeline 执行写作。

用法：
    from src.skills import director_mode

    # 启动 Director 模式
    await director_mode.activate("qiewei_v2")

    # 写一章（Director 模式）
    result = await director_mode.write_chapter(11)

    # 批量写（Director 模式）
    result = await director_mode.batch_write(11, 15)

    # 获取导演报告
    report = await director_mode.get_director_report()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class WritingBrief:
    """写作简报（Director → Writer）"""
    chapter_outline: str = ""
    opening_hook: str = ""  # 上章悬念
    closing_hook: str = ""  # 本章结尾悬念
    foreshadowing_plant: list[str] = field(default_factory=list)  # 需要埋设的伏笔
    foreshadowing_payoff: list[str] = field(default_factory=list)  # 需要回收的伏笔
    characters: list[dict] = field(default_factory=list)  # 本章出场角色
    scenes: list[str] = field(default_factory=list)  # 场景约束
    previous_ending: str = ""  # 上章结尾
    thread_context: str = ""  # 多线叙事进展
    target_tension: int = 5  # 目标紧张度 1-10
    sensory_focus: str = ""  # 感官描写重点
    information_asymmetry: list[str] = field(default_factory=list)  # 信息不对称
    opening_style: str = ""  # 开头方式：dialogue/action/flashback/atmosphere/mystery
    paragraph_plan: list[dict] = field(default_factory=list)  # 段落级规划 [{purpose, focus, length}]
    pov_structure: list[dict] = field(default_factory=list)  # 多视角结构 [{pov, purpose, reveal}]
    world_context: str = ""  # 世界线背景（天下大势）


@dataclass
class DirectorReport:
    """导演报告"""
    novel_id: str
    current_chapter: int
    written_chapters: list[int]
    outline_chapters: int
    rhythm_analysis: str = ""
    foreshadowing_status: list[dict] = field(default_factory=list)
    character_arcs: list[dict] = field(default_factory=list)
    writing_brief: Optional[WritingBrief] = None
    qa_focus: list[str] = field(default_factory=list)


class DirectorMode:
    """
    Director 模式 - 总控规划官

    职责：
    1. 全局状态分析 - 进度、节奏、伏笔、多线叙事
    2. 战前分析 - 每章开写前做 LLM 推理
    3. 生成 WritingBrief - 给 Writer 的精炼指令
    4. 指挥 Pipeline - 执行写作 + 审查
    5. 质量把关 - 审查结果，决定是否需要修改
    """

    def __init__(self):
        self._novel_id: str = ""
        self._novel_dir: Path | None = None
        self._outline: dict | None = None
        self._world_setting: dict | None = None
        self._characters: dict | None = None
        self._session: Any = None  # Lazy load
        self._initialized: bool = False
        self._written_chapters: list[int] = []
        self._rhythm_sequence: list[int] = []  # 节奏序列

    async def activate(self, novel_id: str) -> DirectorReport:
        """
        激活 Director 模式

        初始化项目，分析全局状态，生成导演报告
        """
        self._novel_id = novel_id
        self._novel_dir = Path(f"data/novels/{novel_id}")

        # 加载项目数据
        self._outline = self._load_json("outline.json")
        self._world_setting = self._load_json("world_setting.json")
        self._characters = self._load_json("characters.json")

        # 初始化 session
        from src.config import load_config
        load_config("config/settings.yaml")

        # 导入 session
        from src.skills_core import session as main_session
        await main_session.init(novel_id)
        self._session = main_session

        # 统计已写章节
        self._written_chapters = self._get_written_chapters()

        # 加载节奏序列
        self._rhythm_sequence = self._load_rhythm_sequence()

        self._initialized = True

        # 生成导演报告
        return await self._generate_director_report()

    def _ensure_init(self) -> None:
        if not self._initialized:
            raise RuntimeError("请先调用 await director_mode.activate(novel_id)")

    def _load_json(self, filename: str) -> dict | None:
        path = self._novel_dir / filename if self._novel_dir else Path(filename)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _load_chapter(self, chapter_num: int) -> str | None:
        path = self._novel_dir / "chapters" / f"ch_{chapter_num:03d}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _get_written_chapters(self) -> list[int]:
        """获取已写章节列表"""
        chapters_dir = self._novel_dir / "chapters"
        if not chapters_dir.exists():
            return []
        return sorted(
            int(p.stem.split("_")[1])
            for p in chapters_dir.glob("ch_*.md")
        )

    def _load_rhythm_sequence(self) -> list[int]:
        """加载节奏序列（从 memory 中读取）"""
        if not self._session or not self._session._memory:
            return []

        try:
            rhythm_data = self._session._memory.long_term.get_rhythm_sequence()
            return [item["tension_score"] for item in rhythm_data]
        except Exception:
            return []

    def _get_chapter_outline(self, chapter_num: int) -> dict | None:
        """获取某章大纲"""
        if not self._outline:
            return None
        for vol in self._outline.get("volumes", []):
            for ch in vol.get("chapters", []):
                if ch.get("chapter_number") == chapter_num:
                    return ch
        return None

    async def _generate_director_report(self) -> DirectorReport:
        """生成导演报告"""
        self._ensure_init()

        # 节奏分析
        rhythm_analysis = self._analyze_rhythm()

        # 伏笔状态
        foreshadowing_status = self._get_foreshadowing_status()

        # 角色弧线
        character_arcs = self._get_character_arcs()

        return DirectorReport(
            novel_id=self._novel_id,
            current_chapter=max(self._written_chapters, default=0) + 1,
            written_chapters=self._written_chapters,
            outline_chapters=self._get_outline_chapter_count(),
            rhythm_analysis=rhythm_analysis,
            foreshadowing_status=foreshadowing_status,
            character_arcs=character_arcs,
        )

    def _analyze_rhythm(self) -> str:
        """分析节奏曲线"""
        if not self._session or not self._session._memory:
            return "记忆系统未初始化"

        try:
            analysis = self._session._memory.long_term.get_rhythm_analysis()
            return analysis.get("suggestion", "数据不足，无法分析节奏趋势")
        except Exception:
            return "数据不足，无法分析节奏趋势"

    def _get_foreshadowing_status(self) -> list[dict]:
        """获取伏笔状态"""
        if not self._session or not self._session._memory:
            return []

        try:
            return self._session._memory.long_term.get_foreshadowing_status()
        except Exception:
            return []

    def _get_character_arcs(self) -> list[dict]:
        """获取角色弧线"""
        if not self._characters:
            return []

        arcs = []
        for char_name, char_data in self._characters.get("characters", {}).items():
            arcs.append({
                "name": char_name,
                "current_status": char_data.get("current_status", {}),
                "goals": char_data.get("goals", []),
            })
        return arcs

    def _get_outline_chapter_count(self) -> int:
        """获取大纲章节总数"""
        if not self._outline:
            return 0
        total = 0
        for vol in self._outline.get("volumes", []):
            total += len(vol.get("chapters", []))
        return total

    async def generate_writing_brief(self, chapter_num: int) -> WritingBrief:
        """
        生成写作简报（Director 核心职责）

        战前分析：
        1. 审视全局 - 大纲完成度、节奏曲线、伏笔状态、多线进展
        2. 生成 WritingBrief - 精炼指令给 Writer
        3. 生成 QA 重点 - 给质检 pipeline
        """
        self._ensure_init()

        outline = self._get_chapter_outline(chapter_num)
        if not outline:
            raise ValueError(f"第{chapter_num}章无大纲")

        # 获取上章结尾
        prev_ending = ""
        if chapter_num > 1:
            prev_content = self._load_chapter(chapter_num - 1)
            if prev_content:
                # 提取最后 200 字
                lines = prev_content.strip().split("\n")
                prev_ending = "\n".join(lines[-3:])[:200]

        # 节奏分析 - 设定目标紧张度（使用 MemoryManager 新接口）
        target_tension = 5
        rhythm_suggestion = ""
        if self._session and self._session._memory:
            try:
                rhythm_directive = self._session._memory.get_rhythm_directive(chapter_num)
                target_tension = rhythm_directive.get("target_tension", 5)
                rhythm_suggestion = rhythm_directive.get("suggestion", "")
            except Exception:
                pass

        # 伏笔检查 - 到期伏笔需要回收（使用 MemoryManager 新接口）
        foreshadowing_plant = []
        foreshadowing_payoff = []
        if self._session and self._session._memory:
            try:
                foreshadowing_directive = self._session._memory.get_foreshadowing_directive(chapter_num)
                foreshadowing_plant = foreshadowing_directive.get("plant", [])
                foreshadowing_payoff = foreshadowing_directive.get("payoff", [])
            except Exception:
                pass

        # 角色指令 - 只取本章出场角色
        characters = []
        involved = outline.get("involved_characters", [])
        if self._characters:
            for char_name in involved:
                char_data = self._characters.get("characters", {}).get(char_name, {})
                characters.append({
                    "name": char_name,
                    "current_state": char_data.get("current_status", {}).get("location", ""),
                    "voice": char_data.get("voice", {}),
                })

        # 信息不对称（REQUIREMENTS.md 8.5）
        information_asymmetry = self._generate_information_asymmetry(outline, characters)

        # 开头多样性检查 - 避免套路化
        opening_style = self._analyze_opening_pattern(chapter_num)

        # 段落级规划
        paragraph_plan = self._generate_paragraph_plan(chapter_num, outline, opening_style)

        # 多视角结构 - 避免单一视角
        pov_structure = self._generate_pov_structure(chapter_num, outline)

        # 世界线展开 - 根据章节位置加入大势信息
        world_context = self._get_world_context(chapter_num)

        return WritingBrief(
            chapter_outline=outline.get("summary", ""),
            opening_hook=f"上章结尾：{prev_ending}",
            closing_hook=outline.get("emotional_arc", {}).get("end", ""),
            foreshadowing_plant=foreshadowing_plant,
            foreshadowing_payoff=foreshadowing_payoff,
            characters=characters,
            scenes=[s.get("description", "") if isinstance(s, dict) else str(s)
                    for s in outline.get("key_scenes", [])],
            previous_ending=prev_ending,
            thread_context=self._get_thread_context(chapter_num),
            target_tension=target_tension,
            sensory_focus=self._get_sensory_focus(chapter_num),
            information_asymmetry=information_asymmetry,
            opening_style=opening_style,
            paragraph_plan=paragraph_plan,
            pov_structure=pov_structure,
            world_context=world_context,
        )

    def _get_world_context(self, chapter_num: int) -> str:
        """
        生成世界线背景（天下大势）

        北魏末年（528-532 年）历史背景：
        - 胡太后专权，与孝明帝母子不和
        - 尔朱荣崛起于晋阳，图谋天下
        - 六镇起义此起彼伏
        - 南梁萧衍伺机北伐
        - 未来枭雄：高欢、宇文泰、贺拔岳等尚在尔朱荣麾下

        根据章节位置，逐步展开各条世界线
        """
        # 每 10 章展开一条新的世界线
        world_lines = [
            "洛阳宫廷：胡太后与孝明帝权力斗争白热化",
            "晋阳：尔朱荣练兵蓄锐，图谋不轨",
            "六镇：起义军蜂起，边镇失控",
            "建康：南梁萧衍整顿军备，伺机北伐",
            "河北：葛荣聚众数十万，称帝建国",
        ]

        # 计算当前应展开的世界线
        active_lines = world_lines[:min(len(world_lines), (chapter_num - 1) // 10 + 1)]

        # 根据章节位置，突出某条线
        highlight_idx = (chapter_num - 1) % len(world_lines)
        if highlight_idx < len(active_lines):
            active_lines[highlight_idx] = "**" + active_lines[highlight_idx] + "**"

        return " | ".join(active_lines)

    def _generate_information_asymmetry(self, outline: dict, characters: list[dict]) -> list[str]:
        """生成信息不对称表（REQUIREMENTS.md 8.5）"""
        # 根据角色已知信息生成
        asymmetry = []
        for char in characters:
            knows = char.get("voice", {}).get("knows", [])
            # 简单示例，实际应该从角色状态读取
        return asymmetry

    def _get_thread_context(self, chapter_num: int) -> str:
        """获取多线叙事上下文"""
        # 简化版，实际应该从 StoryThreads 读取
        return f"第{chapter_num}章，主线推进中"

    def _get_sensory_focus(self, chapter_num: int) -> str:
        """获取感官描写重点"""
        # 简化版，实际应该从近章摘要读取
        return "视觉、听觉、触觉"

    def _analyze_opening_pattern(self, chapter_num: int) -> str:
        """
        分析开头模式，避免套路化

        开头方式分类：
        - dialogue: 对话开场
        - action: 动作/事件开场
        - flashback: 回忆/倒叙开场
        - atmosphere: 氛围/环境开场
        - mystery: 悬念/问题开场
        - introspection: 内心独白开场

        检查近 3 章的开头方式，避免连续使用相同模式
        """
        OPENING_STYLES = ['dialogue', 'action', 'flashback', 'atmosphere', 'mystery', 'introspection']

        # 检查近 3 章的开头
        recent_openings = []
        for i in range(max(1, chapter_num - 3), chapter_num):
            content = self._load_chapter(i)
            if content:
                # 提取前 200 字分析
                opening_text = content[:300].lower()

                # 简单启发式分类
                if any(c in opening_text for c in ['"', '"', ''', ''', ':', ':']):
                    recent_openings.append('dialogue')
                elif any(w in opening_text for w in ['突然', '猛地', '瞬间', '轰', '炸', '跑', '冲']):
                    recent_openings.append('action')
                elif any(w in opening_text for w in ['想起', '回忆', '曾经', '那时', '当年']):
                    recent_openings.append('flashback')
                elif any(w in opening_text for w in ['夜', '暮', '晨', '日', '风', '雨', '山', '天']):
                    recent_openings.append('atmosphere')
                elif any(w in opening_text for w in ['为什么', '如何', '难道', '?', '？']):
                    recent_openings.append('mystery')
                else:
                    recent_openings.append('introspection')

        # 选择最少使用的开头方式
        style_counts = {style: recent_openings.count(style) for style in OPENING_STYLES}
        min_count = min(style_counts.values())
        candidates = [s for s, c in style_counts.items() if c == min_count]

        # 优先选择与最近一章不同的方式
        if recent_openings:
            last_opening = recent_openings[-1]
            candidates = [c for c in candidates if c != last_opening] or candidates

        return candidates[0] if candidates else 'action'

    def _generate_paragraph_plan(
        self,
        chapter_num: int,
        outline: dict,
        opening_style: str,
    ) -> list[dict]:
        """
        生成段落级规划

        将章节拆分为 6-8 个段落，每段有明确的目的和重点
        """
        summary = outline.get("summary", "")
        scenes = outline.get("key_scenes", [])

        # 根据大纲场景生成段落规划
        paragraph_plan = []

        # 第一段：开头（根据 opening_style 决定写法）
        paragraph_plan.append({
            "paragraph": 1,
            "purpose": f"开场 - 使用{opening_style}方式",
            "focus": "吸引读者，建立场景",
            "length": "150-200 字",
            "tip": "避免风景描写套路，直接进入情境",
        })

        # 中间段落：场景推进
        for i, scene in enumerate(scenes[:4], start=2):
            scene_desc = scene.get("description", "")[:50] if isinstance(scene, dict) else str(scene)[:50]
            paragraph_plan.append({
                "paragraph": i,
                "purpose": f"场景{i-1} 推进",
                "focus": scene_desc,
                "length": "200-300 字",
                "tip": "保持节奏，避免冗长说明",
            })

        # 最后一段：结尾悬念
        paragraph_plan.append({
            "paragraph": len(paragraph_plan) + 1,
            "purpose": "结尾悬念",
            "focus": outline.get("emotional_arc", {}).get("end", "留下钩子"),
            "length": "100-150 字",
            "tip": "让读者迫不及待想看下一章",
        })

        return paragraph_plan

    def _generate_pov_structure(self, chapter_num: int, outline: dict) -> list[dict]:
        """
        生成多视角结构（避免单一视角）

        POV 类型：
        - protagonist: 主角视角（李曜）
        - antagonist: 反派视角（尔朱荣/追兵）
        - observer: 旁观者视角（元玉奴/路人）
        - omniscient: 上帝视角（大势信息）

        每 3-4 章切换一次主视角，保持悬念
        """
        pov_structure = []

        # 根据章节位置决定视角切换
        # 奇数章：主角视角为主
        # 偶数章：加入反派/旁观者视角

        if chapter_num % 3 == 0:
            # 每 3 章加入一次反派视角
            pov_structure.append({
                "pov": "antagonist",
                "purpose": "展示敌方行动/盘算",
                "reveal": "读者知道但主角不知道的信息",
            })
        elif chapter_num % 5 == 0:
            # 每 5 章加入一次大势视角
            pov_structure.append({
                "pov": "omniscient",
                "purpose": "展示天下大势",
                "reveal": "历史背景/多方势力动向",
            })

        # 默认加入主角视角
        pov_structure.append({
            "pov": "protagonist",
            "purpose": "主角行动/决策",
            "reveal": "主角的已知信息和计划",
        })

        # 有女性角色出场时，加入女性视角
        characters = outline.get("involved_characters", [])
        if any(name in characters for name in ["元玉奴", " Princess"]):
            pov_structure.append({
                "pov": "observer",
                "purpose": "女性角色的内心感受",
                "reveal": "主角看不到的情感细节",
            })

        return pov_structure

    async def write_chapter(
        self,
        chapter_num: int,
        auto_review: bool = True,
        auto_fix: bool = True,
    ) -> dict:
        """
        Director 模式写一章

        流程：
        1. 生成 WritingBrief
        2. 调用 session.write_chapter（完整 Pipeline）
        3. 审查结果，决定是否需要修改
        """
        self._ensure_init()

        # 1. 生成 WritingBrief
        brief = await self.generate_writing_brief(chapter_num)

        # 2. 写作（Pipeline 自动执行）
        result = await self._session.write_chapter(chapter_num)

        if not result.success:
            return {
                "success": False,
                "error": "写作失败",
                "detail": result.error,
            }

        # 3. Director 审查
        if auto_review:
            review_result = await self._review_chapter(chapter_num, brief)

            if not review_result["passed"] and auto_fix:
                # 需要重写
                return await self._rewrite_chapter(chapter_num, brief, review_result)

        return {
            "success": True,
            "chapter": chapter_num,
            "writing_brief": brief,
            "word_count": len(self._load_chapter(chapter_num) or ""),
        }

    async def _review_chapter(self, chapter_num: int, brief: WritingBrief) -> dict:
        """Director 审查章节"""
        content = self._load_chapter(chapter_num)
        if not content:
            return {"passed": False, "reason": "章节不存在"}

        issues = []

        # 检查大纲一致性
        outline = self._get_chapter_outline(chapter_num)
        if outline:
            summary = outline.get("summary", "")
            keywords = summary.split()[:5]
            match_count = sum(1 for kw in keywords if kw in content)
            if match_count < len(keywords) * 0.5:
                issues.append("内容可能与大纲偏离较大")

        # 检查伏笔
        if brief.foreshadowing_payoff:
            for payoff in brief.foreshadowing_payoff:
                if payoff not in content:
                    issues.append(f"伏笔未回收：{payoff}")

        # 检查紧张度
        # （需要调用 EmotionRiskControl）

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    async def _rewrite_chapter(
        self,
        chapter_num: int,
        brief: WritingBrief,
        review: dict,
        max_retries: int = 2,
    ) -> dict:
        """重写章节"""
        for attempt in range(max_retries):
            # 重写
            result = await self._session.write_chapter(chapter_num)
            if not result.success:
                return {
                    "success": False,
                    "error": f"重写失败（尝试{attempt+1}/{max_retries}）",
                    "detail": result.error,
                }

            # 重新审查
            review = await self._review_chapter(chapter_num, brief)
            if review["passed"]:
                break

        return {
            "success": review["passed"],
            "chapter": chapter_num,
            "attempted_rewrites": max_retries,
            "final_issues": review.get("issues", []),
        }

    async def batch_write(
        self,
        start: int,
        end: int,
        auto_review: bool = True,
        auto_fix: bool = True,
    ) -> dict:
        """批量写作（Director 模式）"""
        self._ensure_init()

        results = {}
        for ch in range(start, end + 1):
            result = await self.write_chapter(ch, auto_review, auto_fix)
            results[ch] = result

            if not result["success"]:
                return {
                    "success": False,
                    "message": f"批量写作在第{ch}章中断",
                    "completed": len([r for r in results.values() if r["success"]]),
                    "errors": result.get("error", ""),
                }

        return {
            "success": True,
            "message": f"批量完成：第{start}-{end}章",
            "results": results,
        }

    async def get_director_report(self) -> DirectorReport:
        """获取导演报告"""
        self._ensure_init()
        return await self._generate_director_report()


# ============================================================================
# 全局单例
# ============================================================================

director_mode = DirectorMode()


# CLI 入口
if __name__ == "__main__":
    import asyncio
    import sys

    async def cli():
        if len(sys.argv) < 3:
            print("用法：python -m src.skills.director_mode <novel_id> <command> [args]")
            print("命令：status, write <ch>, batch <start> <end>, report")
            return

        novel_id = sys.argv[1]
        command = sys.argv[2]

        report = await director_mode.activate(novel_id)
        print(f"Director 模式已激活：{novel_id}")
        print(f"已写章节：{report.written_chapters}")
        print(f"下一章：{report.current_chapter}")

        if command == "status":
            print(f"大纲章节：{report.outline_chapters}")
            print(f"节奏分析：{report.rhythm_analysis}")

        elif command == "write" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            result = await director_mode.write_chapter(ch)
            if result["success"]:
                print(f"第{ch}章完成 ({result.get('word_count', '?')}字)")
            else:
                print(f"第{ch}章失败：{result.get('error', '未知')}")

        elif command == "batch" and len(sys.argv) > 4:
            start, end = int(sys.argv[3]), int(sys.argv[4])
            result = await director_mode.batch_write(start, end)
            print(f"结果：{result['message']}")

        elif command == "report":
            full_report = await director_mode.get_director_report()
            print(f"\n=== 导演报告 ===")
            print(f"小说 ID: {full_report.novel_id}")
            print(f"已写章节：{full_report.written_chapters}")
            print(f"下一章：{full_report.current_chapter}")
            print(f"节奏分析：{full_report.rhythm_analysis}")

    asyncio.run(cli())
