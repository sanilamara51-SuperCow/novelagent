"""Rebuild world setting for qiewei_v2 with overpowered protagonist."""
import asyncio
import sys
import os

# Windows 终端编码修复
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from src.config import load_config
load_config('config/settings.yaml')

from src.skills import session
from src.agents.base_agent import AgentInput

async def rebuild():
    r = await session.init('qiewei_v2')
    print(r.content)
    print()

    description = """
穿越历史爽文《窃魏》世界观设定：

【主角金手指】
- 现代军事知识 + 冶金技术 + 火药配方（黑火药、颗粒火药）
- "历史预知"能力：每当重大事件节点前30天，自动获得未来30天的详细情报
- 初始身份：秀容川猎户之子，但身负"天书"（一本随穿越带来的《资治通鉴》残卷）

【核心爽点设计】
1. 武力碾压：主角用现代冶铁法打造"精钢环首刀"，硬度远超北魏铁器
2. 信息差：提前知道尔朱荣河阴之变的名单，救下关键人物收为己用
3. 火药降维：在韩陵之战前掌握火药配方，震撼全场
4. 红颜助力：救下本应死于河阴之变的胡太后侄女、元子攸妹妹等关键女性角色

【势力格局（爽文版）】
- 尔朱荣：初期BOSS，主角先依附再反噬，528年河阴之变时主角已经布局完成，尔朱荣杀人主角救人，收编洛阳残余士族
- 高欢：中期对手，本是主角盟友后反目，531年韩陵之战是全书高潮
- 宇文泰：后期潜在对手，主角提前布局关中，不让宇文氏坐大
- 主角目标：不是做权臣，而是直接"窃魏"——让元氏皇帝禅让，建立新朝

【升级路线】
Ch1-10：秀容川起家，收编流民，打造第一支精钢装备百人队
Ch11-30：依附尔朱荣，做"救火队长"，在河北平叛中积累军功和人望
Ch31-50：河阴之变主角大显身手，救下2000+士族，成为北方士族共主
Ch51-100：与高欢争河北，火药初现，韩陵之战主角以少胜多
Ch101-200：统一北方，改革军制（府兵制前身），最终迫使魏帝禅让

【关键爽文桥段】
- 河阴之变：尔朱荣杀疯了，主角在黄河边设伏救下关键人物，反被尔朱荣赏识，实则暗中收编
- 韩陵之战：主角三千精兵对高欢十万大军，火药包+精钢陌刀阵，一战封神
- 称帝时刻：不是暴力篡位，而是"三让而后受之"，士族、武将、百姓共推

请生成这个世界观的完整JSON，包含era, year_range, political_system, social_structure, geography, key_events, factions, notable_figures, protagonist, main_plot等字段。
"""

    # 直接调用 agent
    raw_result = await session._world_builder.process(
        AgentInput(task_type="world_building", instruction=description)
    )
    print("=" * 60)
    print(f"Raw success: {raw_result.success}")
    print(f"Raw error: {raw_result.error}")
    print(f"Raw content len: {len(raw_result.content)}")
    print(f"Raw content[:300]: {raw_result.content[:300] if raw_result.content else 'empty'}")

    # 现在调用 skill
    result = await session.build_world(description)
    print("\n" + "=" * 60)
    print(f"Skill success: {result.success}")
    print(f"Skill error: {result.error}")

asyncio.run(rebuild())
