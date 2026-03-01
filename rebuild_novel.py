#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新生成世界观和大纲"""

import os
import sys
import io
import json
import asyncio

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config
from src.models.llm_client import LLMClient
from src.agents.world_builder import WorldBuilderAgent
from src.agents.plot_designer import PlotDesignerAgent
from src.agents.base_agent import AgentInput

NOVEL_DIR = Path("data/novels/qiewei_001")

async def generate_world_setting():
    """生成世界观"""
    print("=" * 60)
    print("生成世界观...")
    print("=" * 60)
    
    config = load_config()
    llm_client = LLMClient(config)
    
    # 创建 WorldBuilderAgent
    from types import SimpleNamespace
    agent_config = SimpleNamespace(
        world_builder=SimpleNamespace(
            model="kimi-k2.5",
            max_tokens=8192
        )
    )
    
    world_builder = WorldBuilderAgent(agent_config, llm_client)
    
    # 构建输入
    input_data = AgentInput(
        task_type="world_building",
        context="""请为历史穿越小说《窃魏》设计世界观。

基本要求：
- 类型：穿越历史（男主角）
- 时期：北魏末年，孝昌年间（527-528年）
- 主线：现代特种兵穿越，依附尔朱荣势力，最终建立霸业
- 风格：严肃历史+军事爽文

主角设定：
- 现代特种部队指挥官
- 精通战术、格斗、爆破
- 金手指：超级记忆力+基础化学知识（火药）
- 穿越地点：秀容川

请输出完整的JSON格式世界观，包含：
- era: 时期
- political_system: 政治体制
- social_structure: 社会结构
- geography: 地理
- key_events: 关键历史事件
- factions: 各方势力
- protagonist: 主角设定

重要：必须严格返回JSON格式，不要添加markdown代码块标记，直接返回JSON对象。""",
        instruction="设计详细世界观，要有历史厚重感，适合写长篇章回小说。注意控制篇幅，确保在8192 token内完成。"
    )
    
    # 生成世界观
    output = await world_builder.process(input_data)
    
    if output.success:
        # 保存
        world_file = NOVEL_DIR / "world_setting.json"
        world_file.write_text(output.content, encoding="utf-8")
        print("\n[OK] 世界观已生成！")
        print(f"文件: {world_file}")
        print(f"\n预览:\n{output.content[:500]}...")
        return output.content
    else:
        print(f"[X] 生成失败: {output.error}")
        print(f"\n原始输出 (前2000字符):\n{output.content[:2000]}")
        return None

async def main():
    print("《窃魏》重构 - 使用 Kimi Coding API\n")
    
    # 生成世界观
    world = await generate_world_setting()
    
    if world:
        print("\n" + "=" * 60)
        print("下一步：生成大纲和章节")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
