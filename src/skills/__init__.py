"""
Skills package - 融合番茄小说机制的 Director 模式

导出：
- session: NovelSession 单例
- director_mode: Director 模式（已融合番茄小说机制）
- novel_writer: 写作助手
- novel_reviewer: 审查员
"""

# 从 skills_core 导入核心 session
from src.skills_core import session, NovelSession, SkillResult

# Director 模式（瘦身版 - 数据读取 + Pipeline 调用）
from src.skills.director_mode import (
    DirectorMode,
    director_mode,
    DirectorReport,
)

# 写作技能
from src.skills.novel_writer import NovelWriterSkill, skill as novel_writer_skill

# 审查技能
from src.skills.novel_reviewer import NovelReviewer, reviewer

__all__ = [
    # 核心
    'session',
    'NovelSession',
    'SkillResult',

    # Director 模式（瘦身版）
    'DirectorMode',
    'director_mode',
    'DirectorReport',

    # 写作技能
    'NovelWriterSkill',
    'novel_writer_skill',

    # 审查技能
    'NovelReviewer',
    'reviewer',
]
