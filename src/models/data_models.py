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
