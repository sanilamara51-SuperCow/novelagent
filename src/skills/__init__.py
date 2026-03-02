"""
Skills package - Director 模式的工具集

导出：
- session: NovelSession 单例
- director_mode: Director 模式超级 Skill
- novel_writer: 写作助手
- novel_reviewer: 审查员
"""

# 从 skills_core 导入核心 session
from src.skills_core import session, NovelSession, SkillResult

# 导入子模块
from src.skills.director_mode import DirectorMode, director_mode
from src.skills.novel_writer import NovelWriterSkill, skill as novel_writer_skill
from src.skills.novel_reviewer import NovelReviewer, reviewer

__all__ = [
    # 核心
    'session',
    'NovelSession',
    'SkillResult',
    # Director 模式
    'DirectorMode',
    'director_mode',
    # 其他 skills
    'NovelWriterSkill',
    'novel_writer_skill',
    'NovelReviewer',
    'reviewer',
]
