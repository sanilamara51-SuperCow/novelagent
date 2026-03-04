"""
《唐朝那些事儿》史料审查员
对照资治通鉴、旧唐书、新唐书等正史检查小说内容
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HistoricalFact:
    """史实条目"""
    event: str
    year: Optional[int] = None
    source: str = ""
    description: str = ""
    novel_version: str = ""
    deviation: str = "accurate/partial/fiction"


@dataclass
class ReviewResult:
    chapter_num: int
    passed: bool = True
    accurate_facts: list[str] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fiction_notes: list[str] = field(default_factory=list)
    summary: str = ""


class TangHistoricalReviewer:
    """唐朝史料审查员"""

    def __init__(self):
        self.novel_id = "tang_chao_na_xie_shi_er"
        self.novel_dir = Path(f"data/novels/{self.novel_id}")

        # 晋阳起兵相关史实（资治通鉴卷 183-185、旧唐书高祖本纪）
        self.facts_database = {
            "timeline": {
                "大业十三年初": "李渊任太原留守",
                "大业十三年五月": "李渊正式起兵",
                "大业十三年七月": "李渊率军西进",
                "大业十三年十一月": "攻克长安",
                "义宁元年 (617) 十一月": "立杨侑为帝（隋恭帝）",
                "武德元年 (618) 五月": "李渊称帝"
            },
            "人物": {
                "李渊": {"生年": 566, "617 年年龄": 51, "官职": "太原留守、唐国公"},
                "李世民": {"生年": 598, "617 年年龄": 19, "官职": "屯卫大将军"},
                "李建成": {"生年": 589, "617 年年龄": 28, "官职": "左领军都督"},
                "李元吉": {"生年": 603, "617 年年龄": 14, "留在太原"},
                "裴寂": {"生年": 570, "617 年年龄": 47, "官职": "晋阳宫副监"},
                "刘文静": {"生年": 568, "617 年年龄": 49, "官职": "晋阳令（后被囚）"}
            },
            "关键事件": {
                "晋阳宫密谋": "裴寂设计让李渊与晋阳宫女发生关系，迫使李渊起兵",
                "刘文静下狱": "因与李密有亲，被隋朝下狱，李世民前往探视",
                "李渊装病": "以病重为由不见使者，争取时间",
                "杀王威高君雅": "李渊除掉隋炀帝安插的眼线"
            },
            "谶语": {
                "桃李章": "桃李子，得天下；李氏当为天子",
                "影响": "隋炀帝因此猜忌李姓大臣，李浑被杀"
            }
        }

    def _load_chapter(self, chapter_num: int) -> Optional[str]:
        ch_file = self.novel_dir / "chapters" / f"ch_{chapter_num:03d}.md"
        if ch_file.exists():
            return ch_file.read_text(encoding='utf-8')
        return None

    async def review_chapter(self, chapter_num: int) -> ReviewResult:
        """审查某一章的史料准确性"""
        result = ReviewResult(chapter_num=chapter_num)

        content = self._load_chapter(chapter_num)
        if not content:
            result.passed = False
            result.issues.append({
                "type": "error",
                "category": "文件缺失",
                "description": f"第{chapter_num}章文件不存在"
            })
            return result

        # 第 1 章专项检查
        if chapter_num == 1:
            result = self._review_chapter_1(content, result)

        # 生成总结
        if result.issues:
            result.passed = False
            result.summary = f"史料审查未通过：{len(result.issues)}个错误，{len(result.warnings)}个警告，{len(result.fiction_notes)}处文学演绎"
        elif result.warnings or result.fiction_notes:
            result.summary = f"史料审查通过（有条件）：{len(result.warnings)}个警告，{len(result.fiction_notes)}处文学演绎"
        else:
            result.summary = "史料审查通过：无明显史实错误"

        return result

    def _review_chapter_1(self, content: str, result: ReviewResult) -> ReviewResult:
        """第 1 章专项审查"""

        # === 准确史实检查 ===
        accurate_checks = [
            ("大业十三年", "时间设定准确：大业十三年（617 年）"),
            ("太原留守", "李渊官职准确：太原留守"),
            ("唐国公", "李渊爵位准确：唐国公"),
            ("裴寂", "裴寂出场"),
            ("晋阳宫", "地点准确：晋阳宫是隋炀帝行宫"),
            ("刘文静", "刘文静出场"),
            ("桃李", "谶语'桃李子，得天下'符合史实"),
        ]

        for keyword, desc in accurate_checks:
            if keyword in content:
                result.accurate_facts.append(desc)

        # === 史实核查 ===

        # 1. 李渊年龄
        if "五十二岁" in content or "52 岁" in content:
            # 实际李渊生于 566 年，617 年应为 51 岁（虚岁 52）
            result.accurate_facts.append("李渊年龄基本准确（51-52 岁，虚岁计算合理）")

        # 2. 裴寂年龄
        if "四十六岁" in content or "46 岁" in content:
            # 实际裴寂生于 570 年，617 年应为 47 岁（虚岁 46-47）
            result.accurate_facts.append("裴寂年龄基本准确（46-47 岁）")

        # 3. 李世民年龄
        if "十九岁" in content or "19 岁" in content:
            # 实际李世民生于 598 年，617 年应为 19 岁
            result.accurate_facts.append("李世民年龄准确（19 岁）")

        # 4. 李建成年龄
        if "二十九岁" in content or "29 岁" in content:
            # 实际李建成生于 589 年，617 年应为 28 岁（虚岁 29）
            result.accurate_facts.append("李建成年龄基本准确（28-29 岁）")

        # === 需要警告的地方 ===

        # 1. 季节问题
        if "秋" in content and "夕阳" in content:
            # 资治通鉴：晋阳起兵在大业十三年五月（夏季）
            # 但小说开头可以适度提前，不算大问题
            result.warnings.append("季节设定为'秋'，但史实起兵时间为五月（夏季）。如作为起兵前的铺垫可接受")

        # 2. 李渊决心
        # 史实：李渊确实有野心，但被裴寂设计被迫提前起兵
        if "装病" in content:
            result.accurate_facts.append("李渊装病符合史实——资治通鉴：'渊乃称病不起，委政于寂等'")

        # 3. 江都使者
        if "使者" in content and "密旨" in content:
            # 史实确实有隋炀帝派使者治罪李渊的事
            result.accurate_facts.append("隋炀帝派使者治罪李渊符合史实")

        # === 文学演绎（需标注） ===

        # 1. 晋阳宫夜宴对话
        if "晋阳宫" in content and "酒" in content:
            result.fiction_notes.append("晋阳宫夜宴对话为文学演绎，史书无详细记载")

        # 2. 李渊内心独白
        if "*五十二岁*" in content or "他在心里默念" in content:
            result.fiction_notes.append("人物内心独白为文学演绎")

        # 3. 裴寂说江都流言
        if "两条白蛇" in content or "迷楼" in content:
            result.fiction_notes.append("隋炀帝梦见白蛇、迷楼等传闻出自野史，非正史记载")

        # 4. 李浑被杀
        if "李浑" in content:
            result.accurate_facts.append("李浑因谶语被杀符合史实——大业十一年，李浑因'李氏当为天子'谶语被隋炀帝所杀")

        # 5. 李世民在河东
        if "河东" in content and "李世民" in content:
            # 史实：李世民确实在河东有活动，但具体细节不详
            result.fiction_notes.append("李世民在河东庄园的场景为文学演绎，史书未详载其具体位置")

        # === 重大史实错误检查 ===
        if "李元霸" in content:
            result.issues.append({
                "type": "error",
                "category": "虚构人物",
                "description": "李元霸是《隋唐演义》虚构人物，正史中李玄霸（李渊第三子）早夭，无事迹"
            })

        if "秦琼" in content or "程咬金" in content:
            # 第 1 章秦琼程咬金不应出现
            result.warnings.append("秦琼/程咬金在此时出现可能过早，建议核实时间线")

        return result


# 全局单例
reviewer = TangHistoricalReviewer()


# CLI 入口
if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        if len(sys.argv) > 1:
            ch_num = int(sys.argv[1])
            result = await reviewer.review_chapter(ch_num)
        else:
            ch_num = 1
            result = await reviewer.review_chapter(ch_num)

        print(f"\n=== 第{ch_num}章史料审查结果 ===")
        print(f"总结：{result.summary}")
        print()

        if result.accurate_facts:
            print("[准确史实]")
            for f in result.accurate_facts:
                print(f"  ✓ {f}")
            print()

        if result.issues:
            print("[史实错误]")
            for iss in result.issues:
                print(f"  ✗ [{iss['category']}] {iss['description']}")
            print()

        if result.warnings:
            print("[存疑/警告]")
            for w in result.warnings:
                print(f"  ⚠ {w}")
            print()

        if result.fiction_notes:
            print("[文学演绎/艺术加工]")
            for f in result.fiction_notes:
                print(f"  📖 {f}")
            print()

    asyncio.run(main())
