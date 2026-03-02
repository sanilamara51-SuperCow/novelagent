"""Pydantic v2 data models for the novel agent system."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Character System
# =============================================================================


class CharacterStatus(BaseModel):
    """角色当前状态（每章更新）"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str = ""
    location: str = ""
    position: str = ""
    health: str = "正常"
    mood: str = "平静"
    key_info: List[str] = Field(default_factory=list)


class CharacterEvent(BaseModel):
    """角色经历事件"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    event: str
    timestamp: str = ""


class Character(BaseModel):
    """角色卡片"""

    model_config = ConfigDict(from_attributes=True)

    character_id: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    identity: str = ""
    personality: str = ""
    background: str = ""
    goals: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)
    current_status: CharacterStatus = Field(default_factory=CharacterStatus)
    history: List[CharacterEvent] = Field(default_factory=list)


# =============================================================================
# World
# =============================================================================


class HistoricalEvent(BaseModel):
    """历史事件"""

    model_config = ConfigDict(from_attributes=True)

    year: int
    event: str
    description: str = ""
    changeable: bool = True


class Faction(BaseModel):
    """势力"""

    model_config = ConfigDict(from_attributes=True)

    name: str
    leader: str = ""
    stance: str = ""
    strength: str = ""


class Figure(BaseModel):
    """重要人物"""

    model_config = ConfigDict(from_attributes=True)

    name: str
    identity: str = ""
    personality: str = ""
    current_position: str = ""


class WorldSetting(BaseModel):
    """世界观设定"""

    model_config = ConfigDict(from_attributes=True)

    era: str = ""
    year_range: Tuple[int, int] = (386, 534)
    political_system: str = ""
    social_structure: str = ""
    geography: Dict[str, Any] = Field(default_factory=dict)
    key_events: List[HistoricalEvent] = Field(default_factory=list)
    factions: List[Faction] = Field(default_factory=list)
    notable_figures: List[Figure] = Field(default_factory=list)
    protagonist: Dict[str, Any] = Field(default_factory=dict)
    main_plot: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Story
# =============================================================================


class EmotionalArc(BaseModel):
    """情绪弧线"""

    model_config = ConfigDict(from_attributes=True)

    start: str = "平静"
    peak: str = "紧张"
    end: str = "释然"
    description: str = ""


class Scene(BaseModel):
    """场景"""

    model_config = ConfigDict(from_attributes=True)

    scene_id: str = ""
    description: str
    location: str = ""
    characters: List[str] = Field(default_factory=list)
    mood: str = ""


class DebateConfig(BaseModel):
    """辩论配置"""

    model_config = ConfigDict(from_attributes=True)

    topic: str
    participants: List[str] = Field(default_factory=list)
    stances: Dict[str, str] = Field(default_factory=dict)
    max_rounds: int = 5


class ChapterOutline(BaseModel):
    """章大纲"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    chapter_number: int
    title: str
    summary: str = ""
    key_scenes: List[Scene] = Field(default_factory=list)
    involved_characters: List[str] = Field(default_factory=list)
    historical_events: List[str] = Field(default_factory=list)
    emotional_arc: EmotionalArc = Field(default_factory=EmotionalArc)
    requires_debate: bool = False
    debate_config: Optional[DebateConfig] = None
    # 新增：节奏与多线叙事（REQUIREMENTS.md 10.2）
    target_tension: int = 5  # 目标紧张度 1-10
    active_thread: str = ""  # 本章主线程


class Volume(BaseModel):
    """卷"""

    model_config = ConfigDict(from_attributes=True)

    volume_number: int
    title: str
    summary: str = ""
    chapters: List[ChapterOutline] = Field(default_factory=list)
    emotional_theme: str = ""


class Outline(BaseModel):
    """大纲结构"""

    model_config = ConfigDict(from_attributes=True)

    title: str = ""
    total_chapters: int = 0
    main_storyline: str = ""
    core_conflict: str = ""
    protagonist_arc: str = ""
    volumes: List[Volume] = Field(default_factory=list)
    # 新增：伏笔计划和节奏曲线（REQUIREMENTS.md 10.2）
    foreshadowing_plan: List[dict] = Field(default_factory=list)
    rhythm_curve: List[int] = Field(default_factory=list)  # 每章目标 tension


class Decision(BaseModel):
    """用户决策"""

    model_config = ConfigDict(from_attributes=True)

    decision_id: str = ""
    decision_type: str = ""
    description: str = ""
    options: List[str] = Field(default_factory=list)
    chosen: str = ""
    timestamp: str = ""


class NovelState(BaseModel):
    """小说全局状态"""

    model_config = ConfigDict(from_attributes=True)

    novel_id: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    story_type: str = "time_travel"
    setting: WorldSetting = Field(default_factory=WorldSetting)
    outline: Outline = Field(default_factory=Outline)
    current_volume: int = 1
    current_chapter: int = 1
    phase: str = "init"
    status: str = "idle"
    completed_chapters: List[str] = Field(default_factory=list)
    pending_decisions: List[Decision] = Field(default_factory=list)


# =============================================================================
# Agent I/O
# =============================================================================


class ChapterSummary(BaseModel):
    """章节摘要"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    core_events: List[str] = Field(default_factory=list)
    character_changes: List[Dict[str, Any]] = Field(default_factory=list)
    key_dialogues: List[str] = Field(default_factory=list)
    turning_points: List[str] = Field(default_factory=list)
    cliffhangers: List[str] = Field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)


class ConsistencyIssue(BaseModel):
    """一致性问题"""

    model_config = ConfigDict(from_attributes=True)

    issue_type: str = ""
    severity: str = "warning"
    description: str = ""
    suggestion: str = ""


class ConsistencyReport(BaseModel):
    """一致性报告"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    issues: List[ConsistencyIssue] = Field(default_factory=list)
    passed: bool = True


class RiskIssue(BaseModel):
    """风险问题"""

    model_config = ConfigDict(from_attributes=True)

    category: str = ""
    description: str = ""
    suggestion: str = ""


class RiskReport(BaseModel):
    """风险评估报告"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    tension_score: float = 5.0
    villain_iq: float = 5.0
    protagonist_difficulty: float = 5.0
    arc_match: float = 5.0
    issues: List[RiskIssue] = Field(default_factory=list)
    rewrite_required: bool = False
    suggestions: List[str] = Field(default_factory=list)


class Speech(BaseModel):
    """辩论发言"""

    model_config = ConfigDict(from_attributes=True)

    round: int
    speaker_id: str
    speaker_name: str
    content: str
    emotion: str = ""


class DebateResult(BaseModel):
    """辩论结果"""

    model_config = ConfigDict(from_attributes=True)

    topic: str
    rounds: int = 0
    transcript: List[Speech] = Field(default_factory=list)
    outcome: str = ""
    character_changes: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Director 输出层（REQUIREMENTS.md 10.4）
# =============================================================================


class CharacterBrief(BaseModel):
    """角色简报（给 Writer 的精简版）"""

    model_config = ConfigDict(from_attributes=True)

    name: str
    current_state: str = ""
    voice_summary: str = ""
    knows: List[str] = Field(default_factory=list)
    doesnt_know: List[str] = Field(default_factory=list)


class ForeshadowingDirective(BaseModel):
    """伏笔指令"""

    model_config = ConfigDict(from_attributes=True)

    plant: List[str] = Field(default_factory=list)  # 需要埋设的伏笔
    payoff: List[str] = Field(default_factory=list)  # 需要回收的伏笔


class WritingBrief(BaseModel):
    """写作简报（Director → Writer）"""

    model_config = ConfigDict(from_attributes=True)

    # 基本任务
    chapter_outline: str = ""
    opening_hook: str = ""  # 上章悬念
    closing_hook: str = ""  # 本章结尾悬念

    # 伏笔指令
    foreshadowing: ForeshadowingDirective = Field(default_factory=ForeshadowingDirective)

    # 角色指令（本章出场角色）
    characters: List[CharacterBrief] = Field(default_factory=list)

    # 场景约束
    scenes: List[str] = Field(default_factory=list)

    # 衔接
    previous_ending: str = ""
    thread_context: str = ""

    # 节奏指令
    target_tension: int = 5
    sensory_focus: str = ""

    # 信息不对称（REQUIREMENTS.md 8.5）
    information_asymmetry: List[str] = Field(default_factory=list)


class QAFocus(BaseModel):
    """QA 重点（给质检 pipeline）"""

    model_config = ConfigDict(from_attributes=True)

    consistency_focus: List[str] = Field(default_factory=list)
    style_focus: List[str] = Field(default_factory=list)
    risk_focus: List[str] = Field(default_factory=list)


class ChapterPlan(BaseModel):
    """章节计划（Director 输出）"""

    model_config = ConfigDict(from_attributes=True)

    chapter_number: int
    writing_brief: WritingBrief = Field(default_factory=WritingBrief)
    qa_focus: QAFocus = Field(default_factory=QAFocus)
    outline_adjustments: List[str] = Field(default_factory=list)
    director_notes: str = ""


# =============================================================================
# 新增核心模块数据模型（REQUIREMENTS.md 第 8 节）
# =============================================================================


class Foreshadow(BaseModel):
    """伏笔记录（REQUIREMENTS.md 8.1）"""

    model_config = ConfigDict(from_attributes=True)

    foreshadow_id: str
    description: str
    planted_chapter: int
    expected_payoff_range: List[int] = Field(default_factory=list)  # [start, end]
    payoff_chapter: Optional[int] = None
    status: str = "planted"  # planted | paid_off | overdue | abandoned
    importance: str = "major"  # major | minor
    related_characters: List[str] = Field(default_factory=list)


class CharacterVoice(BaseModel):
    """角色语音卡（REQUIREMENTS.md 8.2）"""

    model_config = ConfigDict(from_attributes=True)

    speech_pattern: str = ""  # "短句、粗口、军事术语"
    verbal_tics: List[str] = Field(default_factory=list)  # 口头禅
    vocabulary_level: str = "common"  # crude | elegant | scholarly | colloquial
    sentence_length: str = "medium"  # very_short | short | medium | long
    emotional_expression: str = "neutral"  # reserved | expressive | suppressed


class StoryThread(BaseModel):
    """多线叙事线程（REQUIREMENTS.md 8.4）"""

    model_config = ConfigDict(from_attributes=True)

    thread_id: str
    name: str
    chapters: List[int] = Field(default_factory=list)
    pov_character: str = ""
    arc: str = ""
    current_progress: int = 0  # 最新推进到的章节


# =============================================================================
# 扩展 Agent 输出层（REQUIREMENTS.md 10.5）
# =============================================================================


class ChapterSummary(BaseModel):
    """章节摘要"""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    core_events: List[str] = Field(default_factory=list)
    character_changes: List[Dict[str, Any]] = Field(default_factory=list)
    key_dialogues: List[str] = Field(default_factory=list)
    turning_points: List[str] = Field(default_factory=list)
    cliffhangers: List[str] = Field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    # 新增
    foreshadowing_planted: List[str] = Field(default_factory=list)
    foreshadowing_paid_off: List[str] = Field(default_factory=list)
    sensory_dimensions: List[str] = Field(default_factory=list)
