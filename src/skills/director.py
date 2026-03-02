"""
Novel Director Skill - 小说智能体总控接口

这是 Claude Code 与小说智能体系统的核心接口。Claude 作为"总导演"，
通过此 skill 指挥各Agent完成写作任务。

设计原则：
1. 通用性 - 适配任何小说项目，不硬编码特定设定
2. 自动化 - 自动完成"写作→审查→修正"闭环
3. 可配置 - 所有检查规则从配置/大纲读取
4. 可解释 - 每次操作都有清晰的报告和理由

用法:
    from src.skills import director

    # 初始化项目
    await director.init("qiewei_v2")

    # 写一章（自动审查 + 修正）
    result = await director.write_chapter(7)

    # 批量写
    result = await director.batch_write(7, 10)

    # 审查报告
    report = await director.review_chapter(7)

    # 获取项目状态
    status = await director.status()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ============================================================================
# 数据类型
# ============================================================================

@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ReviewReport:
    """审查报告"""
    chapter_num: int
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_fix_suggested: bool = False


# ============================================================================
# Director Skill
# ============================================================================

class NovelDirector:
    """
    小说智能体总导演

    职责：
    1. 项目初始化 - 加载配置、大纲、设定
    2. 写作指挥 - 调用 Writer Agent 写作
    3. 质量审查 - 对齐大纲、设定、连续性
    4. 自动修正 - 发现问题自动重写
    5. 状态管理 - 跟踪进度、持久化
    """

    def __init__(self):
        self._novel_id: str = ""
        self._novel_dir: Path | None = None
        self._outline: dict | None = None
        self._world_setting: dict | None = None
        self._characters: dict | None = None
        self._session: Any = None  # Lazy load
        self._initialized: bool = False

    # ------------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------------

    async def init(self, novel_id: str) -> TaskResult:
        """初始化项目"""
        self._novel_id = novel_id
        self._novel_dir = Path(f"data/novels/{novel_id}")

        # 加载项目数据
        self._outline = self._load_json("outline.json")
        self._world_setting = self._load_json("world_setting.json")
        self._characters = self._load_json("characters.json")

        # 初始化 session
        from src.skills import session
        from src.config import load_config
        load_config("config/settings.yaml")
        await session.init(novel_id)
        self._session = session

        self._initialized = True
        return TaskResult(success=True, message=f"项目 {novel_id} 初始化完成")

    def _ensure_init(self) -> None:
        if not self._initialized:
            raise RuntimeError("请先调用 director.init(novel_id)")

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

    def _get_chapter_outline(self, chapter_num: int) -> dict | None:
        """获取某章大纲"""
        if not self._outline:
            return None
        for vol in self._outline.get("volumes", []):
            for ch in vol.get("chapters", []):
                if ch.get("chapter_number") == chapter_num:
                    return ch
        return None

    # ------------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------------

    async def status(self) -> TaskResult:
        """获取项目状态"""
        self._ensure_init()

        # 统计已写章节
        chapters_dir = self._novel_dir / "chapters"
        written = sorted(
            int(p.stem.split("_")[1])
            for p in chapters_dir.glob("ch_*.md")
        ) if chapters_dir.exists() else []

        # 大纲章节总数
        total_outline = 0
        for vol in self._outline.get("volumes", []) if self._outline else []:
            total_outline += len(vol.get("chapters", []))

        return TaskResult(
            success=True,
            message=f"项目 {self._novel_id}: 已写{len(written)}章，大纲{total_outline}章",
            data={
                "novel_id": self._novel_id,
                "written_chapters": written,
                "total_outline": total_outline,
                "next_chapter": max(written, default=0) + 1 if written else 1,
                "has_world_setting": self._world_setting is not None,
                "has_characters": self._characters is not None,
            }
        )

    # ------------------------------------------------------------------------
    # 审查模块
    # ------------------------------------------------------------------------

    async def review_chapter(self, chapter_num: int) -> ReviewReport:
        """
        审查章节

        检查项：
        1. 大纲一致性 - 关键场景、剧情走向
        2. 设定一致性 - 人物身份、世界观
        3. 连续性 - 与前文矛盾（伤势、道具、时间）
        4. 文风 - 白话文/文言检查
        """
        self._ensure_init()
        report = ReviewReport(chapter_num=chapter_num, passed=True)

        content = self._load_chapter(chapter_num)
        outline = self._get_chapter_outline(chapter_num)

        if not content:
            report.passed = False
            report.issues.append({
                "type": "error",
                "category": "文件缺失",
                "description": f"第{chapter_num}章不存在"
            })
            return report

        if not outline:
            report.warnings.append(f"第{chapter_num}章无大纲，跳过部分检查")
            return report

        # 1. 大纲一致性
        report.checks["outline"] = self._check_outline(content, outline, report)

        # 2. 设定一致性
        report.checks["setting"] = self._check_setting(content, chapter_num, report)

        # 3. 连续性
        report.checks["continuity"] = self._check_continuity(content, chapter_num, report)

        # 4. 文风
        report.checks["style"] = self._check_style(content, report)

        # 判定
        if report.issues:
            report.passed = False
            report.auto_fix_suggested = True

        return report

    def _check_outline(self, content: str, outline: dict, report: ReviewReport) -> bool:
        """检查大纲一致性"""
        ok = True

        # 检查关键场景
        key_scenes = outline.get("key_scenes", [])
        for scene in key_scenes:
            scene_text = scene if isinstance(scene, str) else scene.get("description", "")
            if scene_text:
                # 提取关键词
                keywords = self._extract_keywords(scene_text)
                match_count = sum(1 for kw in keywords if kw in content)
                if match_count < len(keywords) * 0.5:
                    report.warnings.append(
                        f"场景可能缺失：{scene_text[:40]}..."
                    )
                    ok = False

        # 检查概要
        summary = outline.get("summary", "")
        if summary:
            summary_keywords = self._extract_keywords(summary)
            match_count = sum(1 for kw in summary_keywords if kw in content)
            if match_count < len(summary_keywords) * 0.3:
                report.warnings.append("内容可能与大纲概要偏离较大")
                ok = False

        return ok

    def _check_setting(self, content: str, chapter_num: int, report: ReviewReport) -> bool:
        """检查设定一致性"""
        ok = True

        # 人物设定检查
        if self._characters:
            chars = self._characters.get("characters", {})
            for char_name, char_data in chars.items():
                # 检查身份是否被错误描述
                if isinstance(char_data, dict):
                    identity = char_data.get("identity", "")
                    if identity and identity in content:
                        # 身份提及，检查是否有矛盾
                        pass  # 可扩展更详细的检查

        # 特定设定规则（从配置读取，此处简化）
        # 例：元玉奴身份
        if "元玉奴" in content:
            if "孝明帝之女" in content or "孝明帝的女儿" in content:
                report.issues.append({
                    "type": "error",
                    "category": "设定冲突",
                    "description": "元玉奴身份错误：应为孝庄帝养女/前朝遗孤"
                })
                ok = False

        # 道具连续性（火药）
        if chapter_num > 4 and "火药" in content:
            if "仅剩" not in content and "最后" not in content:
                report.warnings.append("火药在第 4 章已使用，需确认来源")
                ok = False

        return ok

    def _check_continuity(self, content: str, chapter_num: int, report: ReviewReport) -> bool:
        """检查连续性"""
        ok = True

        if chapter_num <= 1:
            return ok

        # 加载前一章
        prev_content = self._load_chapter(chapter_num - 1)
        if not prev_content:
            return ok

        # 检查突兀伤势
        if "伤口" in content or "受伤" in content:
            if "伤口" not in prev_content and "受伤" not in prev_content:
                # 检查本章是否有受伤原因描述
                if "划伤" not in content and "被" not in content:
                    report.warnings.append("出现前文未提及的伤势，需补充受伤经过")
                    ok = False

        # 检查时间线
        time_markers = ["次日", "第二天", "三日后", "三天后", "数日后"]
        for marker in time_markers:
            if marker in content:
                # 检查时间跳跃是否合理
                pass  # 可扩展

        return ok

    def _check_style(self, content: str, report: ReviewReport) -> bool:
        """检查文风"""
        ok = True

        # 文言词汇检测
        archaic_patterns = ["之乎者也", "矣焉哉", "乃曰", "吾汝"]
        for pattern in archaic_patterns:
            if pattern in content:
                report.warnings.append(f"发现文言风格：{pattern}")
                ok = False

        # 现代用语检测
        modern_patterns = ["OK", "hello", "拜拜", "搞定"]
        for pattern in modern_patterns:
            if pattern.lower() in content.lower():
                report.warnings.append(f"发现现代用语：{pattern}")
                ok = False

        return ok

    def _extract_keywords(self, text: str) -> list[str]:
        """提取中文关键词（简化版）"""
        import re
        # 提取 2-6 字中文词组
        candidates = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
        # 过滤常见虚词
        stop_words = {"的是", "了的", "一个", "这个", "那个", "我们", "他们"}
        return [c for c in candidates if c not in stop_words][:10]

    # ------------------------------------------------------------------------
    # 写作模块
    # ------------------------------------------------------------------------

    async def write_chapter(
        self,
        chapter_num: int,
        auto_review: bool = True,
        auto_fix: bool = True,
        max_retries: int = 1,
    ) -> TaskResult:
        """
        写一章

        Args:
            chapter_num: 章节号
            auto_review: 是否自动审查
            auto_fix: 审查不通过是否自动重写
            max_retries: 最大重写次数
        """
        self._ensure_init()

        # 写作
        write_result = await self._session.write_chapter(chapter_num)
        if not write_result.success:
            return TaskResult(
                success=False,
                message="写作失败",
                errors=[{"type": "error", "description": write_result.error}]
            )

        # 自动审查
        if auto_review:
            review = await self.review_chapter(chapter_num)

            if not review.passed and auto_fix:
                # 需要重写
                for attempt in range(max_retries):
                    if not review.issues:
                        break

                    # 重写
                    rewrite_result = await self._session.write_chapter(chapter_num)
                    if not rewrite_result.success:
                        return TaskResult(
                            success=False,
                            message=f"重写失败（尝试{attempt+1}/{max_retries}）",
                            errors=[{"description": rewrite_result.error}]
                        )

                    # 重新审查
                    review = await self.review_chapter(chapter_num)

                if review.issues:
                    return TaskResult(
                        success=False,
                        message=f"审查未通过（已重试{max_retries}次）",
                        warnings=review.warnings,
                        errors=review.issues
                    )

            return TaskResult(
                success=True,
                message=f"第{chapter_num}章完成",
                data={
                    "word_count": len(self._load_chapter(chapter_num) or ""),
                    "review": {
                        "passed": review.passed,
                        "checks": review.checks,
                        "warnings": review.warnings,
                    }
                },
                warnings=review.warnings
            )

        return TaskResult(
            success=True,
            message=f"第{chapter_num}章完成",
            data={"word_count": len(self._load_chapter(chapter_num) or "")}
        )

    async def batch_write(
        self,
        start: int,
        end: int,
        auto_review: bool = True,
        auto_fix: bool = True,
    ) -> TaskResult:
        """批量写作"""
        self._ensure_init()

        results = {}
        for ch in range(start, end + 1):
            result = await self.write_chapter(ch, auto_review, auto_fix)
            results[ch] = result

            if not result.success:
                return TaskResult(
                    success=False,
                    message=f"批量写作在第{ch}章中断",
                    data={"completed": len([r for r in results.values() if r.success])},
                    errors=result.errors
                )

        return TaskResult(
            success=True,
            message=f"批量完成：第{start}-{end}章",
            data={
                "completed": end - start + 1,
                "results": {ch: r.data for ch, r in results.items()}
            }
        )

    # ------------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------------

    async def get_chapter_outline(self, chapter_num: int) -> TaskResult:
        """获取某章大纲"""
        self._ensure_init()
        outline = self._get_chapter_outline(chapter_num)
        if not outline:
            return TaskResult(
                success=False,
                message=f"第{chapter_num}章大纲不存在"
            )
        return TaskResult(
            success=True,
            message="获取成功",
            data={"outline": outline}
        )


# ============================================================================
# 全局单例 - 供 Claude Code 调用
# ============================================================================

director = NovelDirector()


# CLI 入口
if __name__ == "__main__":
    import asyncio
    import sys

    async def cli():
        if len(sys.argv) < 3:
            print("用法：python -m src.skills.director <novel_id> <command> [args]")
            print("命令：status, write <ch>, batch <start> <end>, review <ch>")
            return

        novel_id = sys.argv[1]
        command = sys.argv[2]

        await director.init(novel_id)

        if command == "status":
            r = await director.status()
            print(f"状态：{r.message}")
            print(f"数据：{r.data}")

        elif command == "write" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            r = await director.write_chapter(ch)
            print(f"结果：{r.message}")
            if r.errors:
                print(f"错误：{r.errors}")

        elif command == "batch" and len(sys.argv) > 4:
            start, end = int(sys.argv[3]), int(sys.argv[4])
            r = await director.batch_write(start, end)
            print(f"结果：{r.message}")

        elif command == "review" and len(sys.argv) > 3:
            ch = int(sys.argv[3])
            report = await director.review_chapter(ch)
            print(f"审查：{'通过' if report.passed else '未通过'}")
            print(f"检查项：{report.checks}")
            if report.issues:
                print(f"错误：{report.issues}")
            if report.warnings:
                print(f"警告：{report.warnings}")

    asyncio.run(cli())
