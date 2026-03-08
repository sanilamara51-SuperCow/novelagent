"""
历史审查员 - 统一史料审查系统

功能：
1. 对齐正史 - 检查与资治通鉴、正史的一致性
2. 对齐大纲 - 检查章节内容是否与 outline.json 一致
3. 对齐设定 - 检查人物设定、世界观是否一致
4. 连续性检查 - 检查与前文是否有矛盾
5. 文风检查 - 确保白话文风格，无文言残留
6. 伏笔追踪 - 追踪伏笔埋设与回收状态

用法：
from src.skills import historical_reviewer

# 审查一章
result = await historical_reviewer.review_chapter(7)
print(result.report)

# 批量审查
results = await historical_reviewer.review_range(1, 20)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class HistoricalFact:
    """史实条目"""
    event: str
    year: Optional[int] = None
    source: str = ""
    description: str = ""
    novel_version: str = ""
    deviation: str = "accurate"  # accurate/partial/fiction


@dataclass
class ContinuityIssue:
    """连续性问题"""
    issue_type: str  # timeline/character/geography/history/outline/style/word_count
    severity: str  # error/warning/info
    description: str
    line_hint: str = ""
    suggestion: str = ""


@dataclass
class ReviewResult:
    """审查结果"""
    chapter_num: int
    passed: bool = True
    outline_match: bool = True
    setting_match: bool = True
    continuity_ok: bool = True
    style_ok: bool = True
    history_accurate: bool = True

    word_count: int = 0
    word_count_passed: bool = True

    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    accurate_facts: list[str] = field(default_factory=list)
    fiction_notes: list[str] = field(default_factory=list)

    foreshadowing_planted: list[str] = field(default_factory=list)
    foreshadowing_paid_off: list[str] = field(default_factory=list)

    summary: str = ""
    suggested_action: str = "none"  # none/review_warnings/rewrite


# ============================================================================
# 历史小说数据库
# ============================================================================

class HistoricalDatabase:
    """历史小说数据库 - 支持多部小说"""

    # 北魏末年 (528-532 年) - 《窃魏》
    QIEWEI_FACTS = {
        "timeline": {
            "528 年": "胡太后毒杀孝明帝，尔朱荣起兵",
            "528 年四月": "河阴之变，尔朱荣屠杀朝臣两千余人",
            "530 年": "孝庄帝杀尔朱荣",
            "531 年": "尔朱兆攻入洛阳，杀孝庄帝",
            "532 年": "高欢击败尔朱氏，掌控朝政",
        },
        "characters": {
            "尔朱荣": {"生年": 493, "官职": "车骑将军、并肆汾广恒云六州讨虏大都督", "封爵": "太原王"},
            "孝庄帝元子攸": {"生年": 507, "528 年年龄": 21, "在位": "528-530 年"},
            "胡太后": {"卒年": 528, "死因": "被尔朱荣沉入黄河"},
            "高欢": {"生年": 496, "528 年官职": "尔朱荣部将"},
            "宇文泰": {"生年": 507, "528 年官职": "鲜于修礼部将"},
        },
        "locations": {
            "洛阳": "北魏都城",
            "晋阳": "尔朱荣大本营（今太原）",
            "河阴": "河阴之变发生地",
            "邺城": "高欢后来的大本营",
        },
    }

    # 唐朝初年 (617-626 年) - 《唐朝那些事儿》
    TANG_FACTS = {
        "timeline": {
            "大业十三年 (617) 五月": "李渊太原起兵",
            "大业十三年 (617) 七月": "李渊率军西进",
            "大业十三年 (617) 十一月": "攻克长安，立杨侑为帝",
            "武德元年 (618) 五月": "李渊称帝，建立唐朝",
            "武德九年 (626) 六月": "玄武门之变",
        },
        "characters": {
            "李渊": {"生年": 566, "617 年年龄": 51, "官职": "太原留守、唐国公"},
            "李世民": {"生年": 598, "617 年年龄": 19, "官职": "屯卫大将军"},
            "李建成": {"生年": 589, "617 年年龄": 28, "官职": "左领军都督"},
            "李元吉": {"生年": 603, "617 年年龄": 14, "留在太原"},
            "裴寂": {"生年": 570, "617 年年龄": 47, "官职": "晋阳宫副监"},
            "刘文静": {"生年": 568, "617 年年龄": 49, "官职": "晋阳令"},
        },
        "events": {
            "晋阳宫密谋": "裴寂设计让李渊与晋阳宫女发生关系，迫使李渊起兵",
            "刘文静下狱": "因与李密有亲，被隋朝下狱，李世民前往探视",
            "李渊装病": "以病重为由不见使者，争取时间",
            "杀王威高君雅": "李渊除掉隋炀帝安插的眼线",
        },
        "prophecies": {
            "桃李章": "桃李子，得天下；李氏当为天子",
            "影响": "隋炀帝因此猜忌李姓大臣，李浑被杀",
        },
    }

    @classmethod
    def get_database(cls, novel_id: str) -> dict:
        """获取对应小说的史实数据库"""
        databases = {
            "qiewei_v2": cls.QIEWEI_FACTS,
            "qiewei_001": cls.QIEWEI_FACTS,
            "tang_chao_na_xie_shi_er": cls.TANG_FACTS,
            "tang": cls.TANG_FACTS,
        }
        return databases.get(novel_id, cls.QIEWEI_FACTS)


# ============================================================================
# 历史审查员主类
# ============================================================================

class HistoricalReviewer:
    """历史审查员 - 统一审查系统"""

    def __init__(self, novel_id: str = "qiewei_v2"):
        self.novel_id = novel_id
        self.novel_dir = Path(f"data/novels/{novel_id}")
        self.db = HistoricalDatabase.get_database(novel_id)

        # 加载项目数据 - 优先读取 chapters_1_20_outline.json（如果存在）
        self.outline = self._load_json("chapters_1_20_outline.json")
        if not self.outline:
            self.outline = self._load_json("outline.json")
        self.world = self._load_json("world_setting.json")
        self.characters = self._load_json("characters.json")

        # 伏笔追踪
        self.foreshadowing_log = self._load_foreshadowing_log()

    def _load_json(self, filename: str) -> Optional[dict]:
        """加载 JSON 文件"""
        path = self.novel_dir / filename
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _load_foreshadowing_log(self) -> dict:
        """加载伏笔追踪日志"""
        log_file = self.novel_dir / "foreshadowing_log.json"
        if log_file.exists():
            return json.loads(log_file.read_text(encoding="utf-8"))
        return {"planted": {}, "paid_off": []}

    def _load_chapter(self, chapter_num: int) -> Optional[str]:
        """加载章节内容"""
        ch_file = self.novel_dir / "chapters" / f"ch_{chapter_num:03d}.md"
        if ch_file.exists():
            content = ch_file.read_text(encoding="utf-8")
            # 移除标题行
            lines = content.split("\n")
            if lines and lines[0].startswith("##"):
                return "\n".join(lines[1:])
            return content
        return None

    def _get_chapter_outline(self, chapter_num: int) -> Optional[dict]:
        """获取某章大纲"""
        if not self.outline:
            return None
        for vol in self.outline.get("volumes", []):
            for ch in vol.get("chapters", []):
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
            result.suggested_action = "write"
            return result

        # 2. 字数检查
        result.word_count = len(content.split())
        if result.word_count < 2000:
            result.word_count_passed = False
            result.issues.append({
                "type": "error",
                "category": "字数不足",
                "description": f"字数仅{result.word_count}字，需扩充到 2500-3500 字"
            })
        elif result.word_count > 4500:
            result.word_count_passed = False
            result.warnings.append(f"字数{result.word_count}字，超出 4500 字上限，建议删减")

        # 3. 大纲检查
        outline = self._get_chapter_outline(chapter_num)
        if outline:
            result = self._check_outline(content, outline, result)
        else:
            result.warnings.append("无大纲，无法进行完整审查")

        # 4. 史实检查
        result = self._check_history(content, chapter_num, result)

        # 5. 设定检查
        result = self._check_setting(content, chapter_num, result)

        # 6. 连续性检查
        result = self._check_continuity(content, chapter_num, result)

        # 7. 文风检查
        result = self._check_style(content, result)

        # 8. 伏笔追踪
        result = self._track_foreshadowing(content, chapter_num, result)

        # 9. 生成总结和建议
        result = self._generate_summary(result)

        return result

    def _check_outline(self, content: str, outline: dict, result: ReviewResult) -> ReviewResult:
        """检查大纲符合度"""
        expected_title = outline.get("title", "")
        summary = outline.get("summary", "")
        key_scenes = outline.get("key_scenes", [])

        # 标题检查
        if expected_title and expected_title not in content[:200]:
            result.warnings.append(f"标题可能不匹配：大纲为《{expected_title}》")

        # 关键场景检查
        for scene in key_scenes:
            scene_text = scene if isinstance(scene, str) else scene.get("description", "")
            if scene_text:
                keywords = re.findall(r"[\u4e00-\u9fa5]{2,6}", scene_text)
                match_count = sum(1 for kw in keywords[:5] if kw in content)
                if match_count < 2:
                    result.warnings.append(f"可能缺少场景：{scene_text[:30]}...")

        # 概要符合度
        if summary:
            summary_keywords = summary.split()[:8]
            match_count = sum(1 for kw in summary_keywords if kw in content)
            if match_count < len(summary_keywords) * 0.5:
                result.issues.append({
                    "type": "warning",
                    "category": "大纲偏离",
                    "description": "内容可能与大纲核心事件偏离较大"
                })
                result.outline_match = False

        return result

    def _check_history(self, content: str, chapter_num: int, result: ReviewResult) -> ReviewResult:
        """检查历史准确性"""
        timeline = self.db.get("timeline", {})
        characters = self.db.get("characters", {})
        events = self.db.get("events", {})

        # 时间线检查
        for time_desc, event_desc in timeline.items():
            # 检查是否有时间线冲突
            if chapter_num <= 5 and "618 年" in content and "617 年" not in content:
                result.warnings.append(f"时间线可能跳跃：{time_desc}的事件不应提前出现")

        # 人物年龄检查
        for char_name, info in characters.items():
            if char_name in content:
                expected_age = info.get(f"{617 if '617' in str(timeline) else 528}年年龄")
                if expected_age:
                    age_mentions = re.findall(rf"{char_name}.*?(\d+[十余岁])", content)
                    for age in age_mentions:
                        if str(expected_age) not in age and abs(int(re.findall(r"\d+", age)[0]) - expected_age) > 3:
                            result.warnings.append(f"{char_name}年龄可能有误（应为{expected_age}岁左右）")

        # 特定事件检查（根据小说类型）
        if self.novel_id.startswith("tang"):
            result = self._check_tang_specific(content, result)
        elif self.novel_id.startswith("qiewei"):
            result = self._check_qiewei_specific(content, result)

        return result

    def _check_tang_specific(self, content: str, result: ReviewResult) -> ReviewResult:
        """《唐朝那些事儿》专项检查"""
        # 李元霸检查
        if "李元霸" in content:
            result.issues.append({
                "type": "error",
                "category": "虚构人物",
                "description": "李元霸是《隋唐演义》虚构人物，正史中李玄霸早夭，无事迹"
            })
            result.history_accurate = False

        # 秦琼程咬金过早出现
        if ("秦琼" in content or "程咬金" in content) and self._get_chapter_outline(1):
            # 第 1 章不应出现
            result.warnings.append("秦琼/程咬金在此时出现可能过早，建议核实时间线")

        # 晋阳宫密谋
        if "晋阳宫" in content and "酒" in content:
            result.accurate_facts.append("晋阳宫场景符合史实——裴寂确在此设计李渊")

        # 谶语检查
        if "桃李" in content:
            result.accurate_facts.append("谶语'桃李子，得天下'符合史实")

        return result

    def _check_qiewei_specific(self, content: str, result: ReviewResult) -> ReviewResult:
        """《窃魏》专项检查"""
        # 河阴之变检查
        if "河阴" in content and "屠杀" not in content and "杀戮" not in content:
            result.warnings.append("河阴之变应包含屠杀情节，史实死亡两千余人")

        # 尔朱荣称谓
        if "尔朱荣" in content:
            if "太原王" not in content and "大将军" not in content:
                result.warnings.append("尔朱荣应称'太原王'或'大将军'")

        return result

    def _check_setting(self, content: str, chapter_num: int, result: ReviewResult) -> ReviewResult:
        """检查设定一致性"""
        # 火药检查（《窃魏》第 4 章后应已用完）
        if chapter_num > 4 and self.novel_id.startswith("qiewei"):
            if "火药" in content and "仅剩" not in content and "最后" not in content:
                result.warnings.append("火药相关内容，需确认是否与第 4 章设定冲突")

        # 元玉奴身份检查
        if "元玉奴" in content:
            if "孝明帝之女" in content or "孝明帝的女儿" in content:
                result.issues.append({
                    "type": "error",
                    "category": "设定冲突",
                    "description": "元玉奴身份错误：应为孝庄帝养女/前朝遗孤"
                })
                result.setting_match = False

        return result

    def _check_continuity(self, content: str, chapter_num: int, result: ReviewResult) -> ReviewResult:
        """检查连续性"""
        if chapter_num > 1:
            prev_content = self._load_chapter(chapter_num - 1)
            if prev_content:
                # 突兀的新伤
                if "伤口" in content and "受伤" not in prev_content and "伤口" not in prev_content:
                    result.warnings.append("突然出现前文未提及的伤势")

                # 时间跳跃
                if "三天后" in content or "三日后" in content:
                    if "次日" not in prev_content and "第二天" not in prev_content:
                        result.warnings.append("时间跳跃可能过大")

                # 角色位置
                for char in ["李曜", "元玉奴", "尔朱荣"]:
                    if char in content and char in prev_content:
                        # 简单位置检查
                        if "洛阳" in prev_content and "晋阳" in content and "赶路" not in content:
                            result.warnings.append(f"{char}位置转换可能突兀")

        return result

    def _check_style(self, content: str, result: ReviewResult) -> ReviewResult:
        """检查文风"""
        # 文言词汇检测
        archaic_words = ["之", "乎", "者", "也", "矣", "焉", "哉", "乃", "曰", "吾", "汝", "尔"]
        for word in archaic_words:
            count = content.count(word)
            if count > 50:
                result.warnings.append(f"文言词汇'{word}'出现{count}次，建议减少")
                result.style_ok = False

        # 现代用语检测
        modern_words = ["卧槽", "666", "老铁", "牛逼", "OK", "hello"]
        for word in modern_words:
            if word.lower() in content.lower():
                result.issues.append({
                    "type": "error",
                    "category": "现代用语",
                    "description": f"发现现代用语：{word}"
                })
                result.style_ok = False

        # 英文检测
        if re.search(r"[a-zA-Z]+", content):
            english_words = re.findall(r"[a-zA-Z]{2,}", content)
            if english_words:
                result.issues.append({
                    "type": "error",
                    "category": "英文混入",
                    "description": f"发现英文词汇：{', '.join(english_words[:3])}"
                })
                result.style_ok = False

        # 元叙事词汇
        meta_words = ["穿越者", "主角", "配角", "金手指", "系统"]
        for word in meta_words:
            if word in content:
                result.issues.append({
                    "type": "error",
                    "category": "元叙事",
                    "description": f"不应出现元叙事词汇：{word}"
                })
                result.style_ok = False

        return result

    def _track_foreshadowing(self, content: str, chapter_num: int, result: ReviewResult) -> ReviewResult:
        """追踪伏笔"""
        # 简单伏笔检测
        foreshadowing_keywords = ["暗自记下", "心中一动", "若有所思", "仿佛看到了什么", "却不知道"]

        for kw in foreshadowing_keywords:
            if kw in content:
                result.foreshadowing_planted.append(f"ch{chapter_num}_{kw}")

        # 检查是否有伏笔回收
        if self.foreshadowing_log.get("planted"):
            for plant_ch, plants in self.foreshadowing_log["planted"].items():
                for plant in plants:
                    if plant in content and plant_ch != str(chapter_num):
                        result.foreshadowing_paid_off.append(plant)

        return result

    def _generate_summary(self, result: ReviewResult) -> ReviewResult:
        """生成总结和建议"""
        error_count = len([i for i in result.issues if i.get("type") == "error"])
        warning_count = len(result.warnings)

        if error_count > 0:
            result.passed = False
            result.summary = f"审查未通过：{error_count}个错误，{warning_count}个警告"
            result.suggested_action = "rewrite"
        elif warning_count > 0:
            result.passed = True
            result.summary = f"审查通过（有条件）：{warning_count}个警告"
            result.suggested_action = "review_warnings"
        else:
            result.passed = True
            result.summary = "审查通过：无问题"
            result.suggested_action = "none"

        return result

    async def review_range(self, start_ch: int, end_ch: Optional[int] = None) -> dict:
        """批量审查多章"""
        if end_ch is None:
            chapters_dir = self.novel_dir / "chapters"
            if chapters_dir.exists():
                ch_files = list(chapters_dir.glob("ch_*.md"))
                end_ch = max(int(p.stem.split("_")[1]) for p in ch_files)
            else:
                end_ch = start_ch

        results = {}
        for ch in range(start_ch, end_ch + 1):
            results[ch] = await self.review_chapter(ch)

        return results


# ============================================================================
# 全局单例
# ============================================================================

reviewer = HistoricalReviewer()


def get_reviewer(novel_id: str) -> HistoricalReviewer:
    """获取指定小说的审查员"""
    return HistoricalReviewer(novel_id)


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        if len(sys.argv) < 3:
            print("用法：python -m src.skills.historical_reviewer <novel_id> [chapter_num]")
            print("  不指定章数则审查全部已写章节")
            return

        novel_id = sys.argv[1]
        reviewer = get_reviewer(novel_id)

        if len(sys.argv) > 2:
            ch_num = int(sys.argv[2])
            result = await reviewer.review_chapter(ch_num)

            print(f"\n=== 第{ch_num}章审查结果 ===")
            print(f"状态：{'✅ 通过' if result.passed else '❌ 未通过'}")
            print(f"总结：{result.summary}")
            print(f"建议：{result.suggested_action}")
            print()

            if result.accurate_facts:
                print("[准确史实]")
                for f in result.accurate_facts:
                    print(f"  ✓ {f}")
                print()

            if result.issues:
                print("[错误]")
                for iss in result.issues:
                    print(f"  ✗ [{iss.get('category', 'error')}] {iss.get('description', '')}")
                print()

            if result.warnings:
                print("[警告]")
                for w in result.warnings:
                    print(f"  ⚠ {w}")
                print()

            if result.foreshadowing_planted:
                print("[伏笔埋设]")
                for f in result.foreshadowing_planted:
                    print(f"  📌 {f}")
                print()

            if result.foreshadowing_paid_off:
                print("[伏笔回收]")
                for f in result.foreshadowing_paid_off:
                    print(f"  ✓ {f}")
                print()
        else:
            print("正在批量审查...")
            results = await reviewer.review_range(1)

            passed_count = sum(1 for r in results.values() if r.passed)
            total_count = len(results)

            print(f"\n=== 批量审查结果 ===")
            print(f"通过：{passed_count}/{total_count}")
            print()

            for ch, r in results.items():
                status = "✅" if r.passed else "❌"
                print(f"{status} 第{ch}章：{r.summary}")

    asyncio.run(main())
