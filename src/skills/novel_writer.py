"""
《窃魏》小说写作助手 - 自动化干活 Skill

功能：
1. 自动写作 - 按大纲写章节
2. 自动审查 - 检查大纲一致性、设定一致性、连续性
3. 自动修正 - 发现问题后自动重写
4. 批量处理 - 连续写多章

用法：
from src.skills import novel_writer

# 写一章（自动审查）
result = await novel_writer.write_with_review(chapter_num=7)

# 批量写（自动审查 + 修正）
results = await novel_writer.batch_write(start=7, end=10)

# 审查一章
report = await novel_writer.review_chapter(chapter_num=7)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChapterReview:
    """章节审查报告"""
    chapter_num: int
    passed: bool
    outline_match: bool = True
    setting_match: bool = True
    continuity_ok: bool = True
    style_ok: bool = True
    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_action: str = ""


class NovelWriterSkill:
    """小说写作助手 Skill"""

    def __init__(self, novel_id: str = "qiewei_v2"):
        self.novel_id = novel_id
        self.novel_dir = Path(f"data/novels/{novel_id}")
        self.outline = self._load_outline()
        self.world = self._load_world()

    def _load_json(self, path: Path) -> dict | None:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _load_outline(self) -> dict | None:
        return self._load_json(self.novel_dir / "outline.json")

    def _load_world(self) -> dict | None:
        return self._load_json(self.novel_dir / "world_setting.json")

    def _load_chapter(self, chapter_num: int) -> str | None:
        ch_file = self.novel_dir / "chapters" / f"ch_{chapter_num:03d}.md"
        if ch_file.exists():
            content = ch_file.read_text(encoding="utf-8")
            # 移除标题行
            lines = content.split("\n")
            if lines and lines[0].startswith("##"):
                return "\n".join(lines[1:])
            return content
        return None

    def _get_chapter_outline(self, chapter_num: int) -> dict | None:
        """获取某章的大纲"""
        if not self.outline:
            return None
        for vol in self.outline.get("volumes", []):
            for ch in vol.get("chapters", []):
                if ch.get("chapter_number") == chapter_num:
                    return ch
        return None

    async def review_chapter(self, chapter_num: int) -> ChapterReview:
        """审查某一章"""
        review = ChapterReview(chapter_num=chapter_num)
        content = self._load_chapter(chapter_num)
        outline = self._get_chapter_outline(chapter_num)

        if not content:
            review.passed = False
            review.issues.append({"type": "error", "desc": "章节文件不存在"})
            review.suggested_action = "write"
            return review

        if not outline:
            review.warnings.append("无大纲，无法完整审查")
            review.passed = True
            review.suggested_action = "none"
            return review

        # 1. 大纲一致性检查
        expected_title = outline.get("title", "")
        summary = outline.get("summary", "")
        key_scenes = outline.get("key_scenes", [])

        if expected_title and expected_title not in content[:200]:
            review.warnings.append(f"标题可能不匹配：大纲为《{expected_title}》")

        # 检查关键场景
        for scene in key_scenes:
            scene_text = scene if isinstance(scene, str) else scene.get("description", "")
            if scene_text:
                # 提取关键动词/名词检查
                keywords = re.findall(r"[\u4e00-\u9fa5]{2,6}", scene_text)
                match_count = sum(1 for kw in keywords[:5] if kw in content)
                if match_count < 2:
                    review.warnings.append(f"可能缺少场景：{scene_text[:30]}...")

        # 2. 设定一致性检查
        # 2.1 元玉奴身份
        if "孝明帝之女" in content or "孝明帝的女儿" in content:
            review.issues.append({
                "type": "error",
                "category": "设定冲突",
                "desc": "元玉奴身份错误：应为孝庄帝养女/前朝遗孤"
            })
            review.setting_match = False

        # 2.2 火药检查（第 4 章后应已用完）
        if chapter_num > 4:
            if "火药" in content and "仅剩" not in content and "最后" not in content:
                review.warnings.append("火药相关内容，需确认是否与第 4 章冲突")

        # 3. 连续性检查
        if chapter_num > 1:
            prev_content = self._load_chapter(chapter_num - 1)
            if prev_content:
                # 检查突兀的新伤
                if "伤口" in content and "受伤" not in prev_content and "伤口" not in prev_content:
                    review.warnings.append("突然出现前文未提及的伤势")

                # 检查时间线
                if "三天后" in content or "三日后" in content:
                    if "次日" not in prev_content and "第二天" not in prev_content:
                        review.warnings.append("时间跳跃可能过大")

        # 4. 文风检查
        archaic = ["之乎者也", "矣焉哉"]
        for aw in archaic:
            if aw in content:
                review.warnings.append(f"发现文言词汇：{aw}")
                review.style_ok = False

        # 判定是否通过
        if review.issues:
            review.passed = False
            review.suggested_action = "rewrite"
        elif review.warnings:
            review.passed = True
            review.suggested_action = "review_warnings"
        else:
            review.passed = True
            review.suggested_action = "none"

        return review

    async def write_with_review(self, chapter_num: int, auto_fix: bool = True) -> dict:
        """写一章并自动审查"""
        from src.skills import session
        from src.config import load_config
        load_config("config/settings.yaml")
        await session.init(self.novel_id)

        # 先写
        result = await session.write_chapter(chapter_num)
        if not result.success:
            return {"success": False, "error": "写作失败", "detail": result.error}

        # 审查
        review = await self.review_chapter(chapter_num)

        if not review.passed and auto_fix:
            # 需要重写
            return {
                "success": False,
                "error": "审查未通过，需要重写",
                "review": review,
                "issues": review.issues,
            }

        return {
            "success": True,
            "chapter": chapter_num,
            "review": review,
            "word_count": len(self._load_chapter(chapter_num) or ""),
        }

    async def batch_write(
        self,
        start: int,
        end: int,
        auto_fix: bool = True,
    ) -> dict:
        """批量写作 + 审查"""
        from src.skills import session
        from src.config import load_config
        load_config("config/settings.yaml")
        await session.init(self.novel_id)

        results = {}
        for ch in range(start, end + 1):
            print(f"\n=== 写第{ch}章 ===")
            r = await self.write_with_review(ch, auto_fix)
            results[ch] = r

            if r["success"]:
                print(f"✅ 第{ch}章完成 ({r.get('word_count', '?')}字)")
            else:
                print(f"❌ 第{ch}章失败：{r.get('error', '未知')}")
                if r.get("issues"):
                    for iss in r["issues"]:
                        print(f"   - [{iss.get('category', 'error')}] {iss.get('desc', '')}")
                break  # 停止继续写

        return {
            "success": all(r["success"] for r in results.values()),
            "results": results,
            "completed": sum(1 for r in results.values() if r["success"]),
            "total": end - start + 1,
        }


# 全局单例
skill = NovelWriterSkill()
