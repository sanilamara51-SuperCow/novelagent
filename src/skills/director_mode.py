"""
Director Mode - 导演模式超级 Skill

这是 Director（总控规划官）的核心接口。Claude 作为 Director，
通过自身推理进行战前分析，生成 WritingBrief JSON，指挥 Pipeline 执行写作。

核心架构：
- Claude = 导演大脑（分析决策、生成 Brief、语义审查）
- Python = 执行手脚（数据读取、Brief 注入、Pipeline 调用）

用法：
    from src.skills import director_mode

    # 启动 Director 模式
    await director_mode.activate("qiewei_v2")

    # 收集上下文（给 Claude 做分析）
    ctx = director_mode.collect_context(32)

    # 使用已生成的 Brief 执行写作
    result = await director_mode.write_with_brief(32)

    # 带反馈重写
    result = await director_mode.revise_with_feedback(32, "爽点力度不足...")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class DirectorReport:
    """导演报告 - 全局状态快照"""
    novel_id: str
    current_chapter: int
    written_chapters: list[int]
    outline_chapters: int
    rhythm_analysis: str = ""
    foreshadowing_status: list[dict] = field(default_factory=list)
    character_arcs: list[dict] = field(default_factory=list)


class DirectorMode:
    """
    Director 模式 - 总控规划官（瘦身版）

    职责：
    1. 数据读取工具 - 为 Claude 提供分析所需的上下文
    2. Brief 注入 - 将 Claude 生成的 WritingBrief 注入到 Writer Pipeline
    3. Pipeline 调用 - 执行写作、重写、记忆更新
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

    async def activate(self, novel_id: str) -> DirectorReport:
        """
        激活 Director 模式

        初始化项目，加载数据，返回全局状态报告
        """
        self._novel_id = novel_id
        self._novel_dir = Path(f"data/novels/{novel_id}")

        # 加载项目数据 - 优先读取 chapters_1_40_outline.json（如果存在），否则 1-20，最后 outline.json
        self._outline = self._load_json("chapters_1_40_outline.json")
        if not self._outline:
            self._outline = self._load_json("chapters_1_20_outline.json")
        if not self._outline:
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

    def _load_summary(self, chapter_num: int) -> dict | None:
        path = self._novel_dir / "summaries" / f"ch_{chapter_num:03d}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
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

    def _get_chapter_outline(self, chapter_num: int) -> dict | None:
        """获取某章大纲 - 支持两种数据结构"""
        if not self._outline:
            return None

        # 结构 1: chapters_1_20_outline.json - {"chapters": [...]}
        if "chapters" in self._outline:
            for ch in self._outline.get("chapters", []):
                if ch.get("chapter_number") == chapter_num:
                    return ch
            return None

        # 结构 2: outline.json - {"volumes": [{"chapters": [...]}]}
        for vol in self._outline.get("volumes", []):
            for ch in vol.get("chapters", []):
                if ch.get("chapter_number") == chapter_num:
                    return ch
        return None

    def _get_outline_chapter_count(self) -> int:
        """获取大纲章节总数 - 支持两种数据结构"""
        if not self._outline:
            return 0

        # 结构 1: chapters_1_20_outline.json - {"chapters": [...]}
        if "chapters" in self._outline:
            return len(self._outline.get("chapters", []))

        # 结构 2: outline.json - {"volumes": [{"chapters": [...]}]}
        total = 0
        for vol in self._outline.get("volumes", []):
            total += len(vol.get("chapters", []))
        return total

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

    # ========================================================================
    # 核心工具方法 - 为 Claude 导演提供数据
    # ========================================================================

    def collect_context(self, chapter_num: int) -> dict:
        """
        收集 Claude 导演分析所需的全部上下文

        返回 dict 包含：
        - outline: 本章大纲
        - recent_summaries: 近 3 章摘要
        - previous_ending: 上章结尾 500 字
        - character_states: 涉及角色状态
        - world_setting_brief: 世界设定摘要
        - recent_openings: 近 3 章开头方式统计
        """
        self._ensure_init()

        # 本章大纲
        outline = self._get_chapter_outline(chapter_num)

        # 近 3 章摘要
        recent_summaries = []
        for i in range(max(1, chapter_num - 3), chapter_num):
            summary = self._load_summary(i)
            if summary:
                recent_summaries.append(summary)

        # 上章结尾 500 字
        previous_ending = ""
        if chapter_num > 1:
            prev_content = self._load_chapter(chapter_num - 1)
            if prev_content:
                previous_ending = prev_content[-500:]

        # 涉及角色状态
        character_states = {}
        if outline:
            involved = outline.get("involved_characters", [])
            if self._characters:
                for char_name in involved:
                    char_data = self._characters.get("characters", {}).get(char_name, {})
                    character_states[char_name] = {
                        "current_status": char_data.get("current_status", {}),
                        "voice": char_data.get("voice", {}),
                        "goals": char_data.get("goals", []),
                    }

        # 世界设定摘要
        world_setting_brief = ""
        if self._world_setting:
            world_setting_brief = json.dumps({
                "era": self._world_setting.get("era", ""),
                "timeline": self._world_setting.get("timeline", [])[:5],
                "factions": self._world_setting.get("factions", [])[:5],
            }, ensure_ascii=False, indent=2)

        # 近 3 章开头方式统计
        recent_openings = self._analyze_recent_openings(chapter_num)

        return {
            "chapter_number": chapter_num,
            "outline": outline,
            "recent_summaries": recent_summaries,
            "previous_ending": previous_ending,
            "character_states": character_states,
            "world_setting_brief": world_setting_brief,
            "recent_openings": recent_openings,
        }

    def _analyze_recent_openings(self, chapter_num: int) -> list[dict]:
        """分析近 3 章的开头方式，供 Claude 参考避免重复"""
        OPENING_STYLES = ['dialogue', 'action', 'flashback', 'atmosphere', 'mystery', 'introspection']
        results = []

        for i in range(max(1, chapter_num - 3), chapter_num):
            content = self._load_chapter(i)
            if content:
                opening_text = content[:300].lower()

                # 简单启发式分类
                style = 'introspection'
                if any(c in opening_text for c in ['"', '"', ''', ''', ':', ':']):
                    style = 'dialogue'
                elif any(w in opening_text for w in ['突然', '猛地', '瞬间', '轰', '炸', '跑', '冲']):
                    style = 'action'
                elif any(w in opening_text for w in ['想起', '回忆', '曾经', '那时', '当年']):
                    style = 'flashback'
                elif any(w in opening_text for w in ['夜', '暮', '晨', '日', '风', '雨', '山', '天']):
                    style = 'atmosphere'
                elif any(w in opening_text for w in ['为什么', '如何', '难道', '?', '?']):
                    style = 'mystery'

                results.append({
                    "chapter": i,
                    "style": style,
                    "first_100_chars": content[:100],
                })

        return results

    async def get_director_report(self) -> DirectorReport:
        """获取导演报告"""
        self._ensure_init()
        return await self._generate_director_report()

    # ========================================================================
    # 写作执行方法 - 调用 Pipeline
    # ========================================================================

    async def write_with_brief(self, chapter_num: int) -> dict:
        """
        使用已保存的 WritingBrief 执行写作

        前置条件：
        data/novels/{novel_id}/briefs/ch_{NNN}.brief.json 已存在
        （由 Claude 导演分析后保存）
        """
        self._ensure_init()

        brief_path = self._novel_dir / "briefs" / f"ch_{chapter_num:03d}.brief.json"
        if not brief_path.exists():
            return {"success": False, "error": f"WritingBrief not found: {brief_path}"}

        # 调用 session.write_chapter，brief 会被自动检测并注入
        result = await self._session.write_chapter(chapter_num)

        if not result.success:
            return {"success": False, "error": result.error}

        return {
            "success": True,
            "chapter": chapter_num,
            "word_count": len(result.content),
            "brief_path": str(brief_path),
            "data": result.data,
        }

    async def revise_with_feedback(self, chapter_num: int, feedback: str) -> dict:
        """
        Claude 审查后带反馈重写

        Args:
            chapter_num: 章节号
            feedback: Claude 生成的具体修改意见
        """
        self._ensure_init()

        result = await self._session.revise_chapter(chapter_num, feedback)

        return {
            "success": result.success,
            "chapter": chapter_num,
            "word_count": len(result.content) if result.content else 0,
            "error": result.error,
        }

    async def update_memory(self, chapter_num: int) -> dict:
        """更新记忆系统（写作完成后的收尾工作）"""
        self._ensure_init()

        result = await self._session.update_memory(chapter_num)

        return {
            "success": result.success,
            "chapter": chapter_num,
        }

    async def get_chapter_status(self, chapter_num: int) -> dict:
        """获取某章的状态（用于 Claude 审查）"""
        self._ensure_init()

        # 读取章节
        content = self._load_chapter(chapter_num)
        if not content:
            return {"exists": False, "error": "章节不存在"}

        # 读取摘要
        summary = self._load_summary(chapter_num)

        # 字数统计（中文）
        import re
        word_count = len(re.sub(r'\s+', '', content))

        return {
            "exists": True,
            "word_count": word_count,
            "content_preview": content[:500],
            "content_ending": content[-300:],
            "summary": summary,
        }

    # ========================================================================
    # 数据保存方法 - 保存 Claude 生成的 Brief
    # ========================================================================

    def save_brief(self, chapter_num: int, brief: dict) -> Path:
        """
        保存 Claude 生成的 WritingBrief 到 JSON 文件

        Args:
            chapter_num: 章节号
            brief: WritingBrief dict（由 Claude 生成）

        Returns:
            保存的文件路径
        """
        self._ensure_init()

        briefs_dir = self._novel_dir / "briefs"
        briefs_dir.mkdir(exist_ok=True)

        brief_path = briefs_dir / f"ch_{chapter_num:03d}.brief.json"
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

        return brief_path


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
            print("命令:")
            print("  status                      - 查看项目状态")
            print("  report                      - 生成导演报告")
            print("  collect-context <ch>        - 收集上下文（给 Claude 分析）")
            print("  write-with-brief <ch>       - 使用 Brief 执行写作")
            print("  revise <ch> --feedback \"..\" - 带反馈重写")
            print("  update-memory <ch>          - 更新记忆")
            return

        novel_id = sys.argv[1]
        command = sys.argv[2]

        # 激活
        report = await director_mode.activate(novel_id)
        print(f"Director 模式已激活：{novel_id}")
        print(f"已写章节：{report.written_chapters}")
        print(f"下一章：{report.current_chapter}")

        if command == "status":
            print(f"大纲章节：{report.outline_chapters}")
            print(f"节奏分析：{report.rhythm_analysis}")

        elif command == "report":
            full_report = await director_mode.get_director_report()
            print(f"\n=== 导演报告 ===")
            print(f"小说 ID: {full_report.novel_id}")
            print(f"已写章节：{full_report.written_chapters}")
            print(f"下一章：{full_report.current_chapter}")
            print(f"节奏分析：{full_report.rhythm_analysis}")

        elif command == "collect-context" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            ctx = director_mode.collect_context(ch)
            print(f"\n=== 第{ch}章上下文 ===")
            print(f"大纲：{json.dumps(ctx['outline'], ensure_ascii=False, indent=2) if ctx['outline'] else '无'}")
            print(f"\n近 3 章摘要数量：{len(ctx['recent_summaries'])}")
            print(f"上章结尾字数：{len(ctx['previous_ending'])}")
            print(f"涉及角色：{list(ctx['character_states'].keys())}")
            print(f"\nJSON 输出：")
            print(json.dumps(ctx, ensure_ascii=False, indent=2))

        elif command == "write-with-brief" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            result = await director_mode.write_with_brief(ch)
            if result["success"]:
                print(f"第{ch}章完成 ({result.get('word_count', '?')}字)")
                print(f"Brief 路径：{result.get('brief_path')}")
            else:
                print(f"第{ch}章失败：{result.get('error', '未知')}")

        elif command == "revise" and len(sys.argv) > 4:
            ch = int(sys.argv[3])
            # 解析 --feedback 参数
            feedback = ""
            for i, arg in enumerate(sys.argv[4:], start=4):
                if arg == "--feedback" and i + 1 < len(sys.argv):
                    feedback = sys.argv[i + 1]
                    break
            if not feedback:
                print("错误：请提供 --feedback 参数")
                return
            result = await director_mode.revise_with_feedback(ch, feedback)
            if result["success"]:
                print(f"第{ch}章重写完成 ({result.get('word_count', '?')}字)")
            else:
                print(f"第{ch}章重写失败：{result.get('error', '未知')}")

        elif command == "update-memory" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            result = await director_mode.update_memory(ch)
            if result["success"]:
                print(f"第{ch}章记忆已更新")
            else:
                print(f"第{ch}章记忆更新失败：{result.get('error', '未知')}")

        elif command == "chapter-status" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            status = await director_mode.get_chapter_status(ch)
            print(f"第{ch}章状态：{json.dumps(status, ensure_ascii=False, indent=2)}")

    asyncio.run(cli())
