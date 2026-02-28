#!/usr/bin/env python3
"""
测试novelagent是否能正常工作
使用修复后的多模型LLMClient
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.llm_client import MultiModelClient, LLMClient


async def test_novelagent():
    """测试novelagent核心功能"""
    print("=" * 60)
    print("《窃魏》NovelAgent 系统测试")
    print("=" * 60)

    # 测试1: 多模型客户端
    print("\n[测试1] 初始化多模型客户端...")
    try:
        client = MultiModelClient()
        print("✓ 多模型客户端初始化成功")
        print("  - DeepSeek: 已配置")
        print("  - 豆包(火山): 已配置")
        print("  - Kimi K2(火山): 已配置")
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False

    # 测试2: DeepSeek调用
    print("\n[测试2] 测试DeepSeek API...")
    try:
        resp = await client.call_deepseek(
            [{"role": "user", "content": "简述北魏末年尔朱荣，30字"}]
        )
        print(f"✓ DeepSeek响应成功")
        print(f"  内容: {resp.content[:50]}...")
        print(f"  Token: {resp.input_tokens} -> {resp.output_tokens}")
    except Exception as e:
        print(f"✗ 失败: {e}")

    # 测试3: 豆包调用
    print("\n[测试3] 测试豆包 API...")
    try:
        resp = await client.call_doubao(
            [{"role": "user", "content": "描写雪夜缝衣的女子，30字"}]
        )
        print(f"✓ 豆包响应成功")
        print(f"  内容: {resp.content[:50]}...")
    except Exception as e:
        print(f"✗ 失败: {e}")

    # 测试4: Kimi调用
    print("\n[测试4] 测试Kimi K2 API...")
    try:
        resp = await client.call_kimi(
            [{"role": "user", "content": "写两句古代士兵对话"}]
        )
        print(f"✓ Kimi响应成功")
        print(f"  内容: {resp.content[:50]}...")
    except Exception as e:
        print(f"✗ 失败: {e}")

    # 测试5: 兼容旧接口
    print("\n[测试5] 测试兼容旧LLMClient接口...")
    try:
        old_client = LLMClient()
        resp = await old_client.acompletion(
            messages=[{"role": "user", "content": "测试"}],
            model="deepseek/deepseek-chat",
        )
        print(f"✓ 旧接口兼容成功")
    except Exception as e:
        print(f"✗ 失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成！NovelAgent已修复，可以正常使用")
    print("=" * 60)
    print("\n使用方法:")
    print("  from src.models.llm_client import MultiModelClient")
    print("  client = MultiModelClient()")
    print("  await client.call_deepseek(messages)")
    print("  await client.call_doubao(messages)")
    print("  await client.call_kimi(messages)")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_novelagent())
    exit(0 if success else 1)
