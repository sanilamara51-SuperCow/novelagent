import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.llm_client import MultiModelClient

async def test():
    print("NovelAgent Multi-Model Test")
    print("=" * 50)
    
    client = MultiModelClient()
    print("[OK] Client initialized")
    
    print("\nTest 1: DeepSeek...")
    resp = await client.call_deepseek([
        {"role": "user", "content": "简述北魏末年，20字"}
    ])
    print(f"Response: {resp.content[:50]}...")
    
    print("\nTest 2: Doubao...")
    resp = await client.call_doubao([
        {"role": "user", "content": "描写雪夜女子，20字"}
    ])
    print(f"Response: {resp.content[:50]}...")
    
    print("\nTest 3: Kimi...")
    resp = await client.call_kimi([
        {"role": "user", "content": "写两句士兵对话"}
    ])
    print(f"Response: {resp.content[:50]}...")
    
    print("\n" + "=" * 50)
    print("All tests passed!")

asyncio.run(test())
