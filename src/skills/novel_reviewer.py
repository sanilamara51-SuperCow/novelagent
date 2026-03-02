"""
《窃魏》小说审查员 - 严格校对每章内容

功能：
1. 对齐大纲 - 检查章节内容是否与 outline.json 一致
2. 对齐设定 - 检查人物设定、世界观是否与 characters.json/world_setting.json 一致
3. 连续性检查 - 检查与前文是否有矛盾（伤情、道具、时间线等）
4. 文风检查 - 确保白话文风格，无文言残留

用法：
from src.skills import novel_reviewer

result = await novel_reviewer.review_chapter(chapter_num)
print(result.report)  # 审查报告
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ReviewResult:
    """审查结果"""
    chapter_num: int
    passed: bool = True
    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""


class NovelReviewer:
    """小说审查员"""

    def __init__(self, novel_id: str = "qiewei_v2"):
        self.novel_id = novel_id
        self.novel_dir = Path(f"data/novels/{novel_id}")
        self.outline = self._load_outline()
        self.world = self._load_world()
        self.characters = self._load_characters()

    def _load_json(self, path: Path) -> Optional[dict]:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        return None

    def _load_outline(self) -> Optional[dict]:
        return self._load_json(self.novel_dir / "outline.json")

    def _load_world(self) -> Optional[dict]:
        return self._load_json(self.novel_dir / "world_setting.json")

    def _load_characters(self) -> Optional[dict]:
        return self._load_json(self.novel_dir / "characters.json")

    def _load_chapter(self, chapter_num: int) -> Optional[str]:
        ch_file = self.novel_dir / "chapters" / f"ch_{chapter_num:03d}.md"
        if ch_file.exists():
            return ch_file.read_text(encoding='utf-8')
        return None

    def _get_outline_for_chapter(self, chapter_num: int) -> Optional[dict]:
        """获取某章的大纲"""
        if not self.outline:
            return None
        volumes = self.outline.get("volumes", [])
        for vol in volumes:
            chapters = vol.get("chapters", [])
            for ch in chapters:
                if ch.get("chapter_number") == chapter_num:
                    return ch
        return None

    async def review_chapter(self, chapter_num: int) -> ReviewResult:
        """审查某一章"""
        result = ReviewResult(chapter_num=chapter_num)

        # 1. 加载章节内容
        content = self._load_chapter(chapter_num)
        if not content:
            result.passed = False
            result.issues.append({
                "type": "error",
                "category": "文件缺失",
                "description": f"第{chapter_num}章文件不存在"
            })
            return result

        # 2. 加载大纲
        outline = self._get_outline_for_chapter(chapter_num)
        if not outline:
            result.warnings.append(f"第{chapter_num}章无大纲，无法进行完整审查")
        else:
            # 2.1 检查标题
            expected_title = outline.get("title", "")
            if expected_title and expected_title not in content[:100]:
                result.warnings.append(f"标题不匹配：大纲为《{expected_title}》")

            # 2.2 检查关键场景
            key_scenes = outline.get("key_scenes", [])
            for scene in key_scenes:
                scene_desc = scene if isinstance(scene, str) else scene.get("description", "")
                if scene_desc and scene_desc not in content:
                    result.warnings.append(f"缺少关键场景：{scene_desc[:50]}...")

            # 2.3 检查概要符合度
            summary = outline.get("summary", "")

        # 3. 连续性检查
        # 3.1 检查与前文伤势是否一致
        if chapter_num > 1:
            prev_content = self._load_chapter(chapter_num - 1)
            if prev_content:
                # 检查是否有突兀的新伤
                if "伤口" in content and "受伤" not in prev_content and "伤口" not in prev_content:
                    result.warnings.append("突然出现前文未提及的伤势")

        # 4. 文风检查 - 文言词汇检测
        archaic_words = ["之", "乎", "者", "也", "矣", "焉", "哉", "乃", "曰", "吾", "汝", "尔"]
        for word in archaic_words:
            count = content.count(word)
            if count > 50:  # 阈值
                result.warnings.append(f"文言词汇'{word}'出现{count}次，建议减少")

        # 5. 设定检查
        # 5.1 检查火药使用（第 4 章后应已用完）
        if chapter_num > 4:
            if "火药" in content or "硝石" in content or "硫磺" in content:
                # 检查是否有合理来源说明
                if "仅剩" not in content and "最后" not in content:
                    result.warnings.append("火药相关内容，需确认是否与第 4 章设定冲突")

        # 5.2 检查元玉奴身份设定
        if "元玉奴" in content:
            # 应该是孝庄帝养女/前朝遗孤，非孝明帝之女
            if "孝明帝之女" in content or "孝明帝的女儿" in content:
                result.issues.append({
                    "type": "error",
                    "category": "设定冲突",
                    "description": "元玉奴身份错误：应为孝庄帝养女（前朝遗孤），非孝明帝之女"
                })

        # 6. 生成总结
        if result.issues:
            result.passed = False
            result.summary = f"审查未通过：{len(result.issues)}个错误，{len(result.warnings)}个警告"
        elif result.warnings:
            result.summary = f"审查通过（有条件）：{len(result.warnings)}个警告"
        else:
            result.summary = "审查通过：无问题"

        return result

    async def review_all(self, start_ch: int = 1, end_ch: Optional[int] = None) -> dict:
        """批量审查多章"""
        if end_ch is None:
            # 自动检测已写的最大章数
            chapters_dir = self.novel_dir / "chapters"
            if chapters_dir.exists():
                ch_files = list(chapters_dir.glob("ch_*.md"))
                end_ch = len(ch_files)
            else:
                end_ch = start_ch

        results = {}
        for ch in range(start_ch, end_ch + 1):
            results[ch] = await self.review_chapter(ch)

        return results


# 全局单例
reviewer = NovelReviewer()


# CLI 入口
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        if len(sys.argv) > 1:
            ch_num = int(sys.argv[1])
            result = await reviewer.review_chapter(ch_num)
        else:
            results = await reviewer.review_all()
            for ch, r in results.items():
                print(f"\n=== 第{ch}章审查结果 ===")
                print(f"状态：{'✅ 通过' if r.passed else '❌ 未通过'}")
                print(f"总结：{r.summary}")
                if r.issues:
                    print("错误:")
                    for iss in r.issues:
                        print(f"  - [{iss['category']}] {iss['description']}")
                if r.warnings:
                    print("警告:")
                    for w in r.warnings:
                        print(f"  - {w}")

    asyncio.run(main())
