import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="257cc276-9d75-47d3-bae2-80301418b833",
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

async def test():
    try:
        resp = await client.chat.completions.create(
            model="doubao-seed-1-8-251228",
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=50
        )
        print("豆包:", resp.choices[0].message.content)
    except Exception as e:
        print("错误:", e)

asyncio.run(test())
