#!/usr/bin/env python3
"""Test DeepSeek API key directly using OpenAI SDK"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
print(f"API Key: {api_key[:25]}..." if api_key else "NOT SET")
print()

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

print("Testing DeepSeek API with Northern Wei history question...")
print()

try:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "你是一位精通北魏史的历史学家。请用简洁的语言回答。",
            },
            {
                "role": "user",
                "content": "请简述528年河阴之变中尔朱荣清洗北魏百官的经过，控制在200字以内。",
            },
        ],
        max_tokens=500,
        temperature=0.7,
    )

    print("[OK] API call successful!")
    print(f"\n模型回复:")
    print("=" * 60)
    print(response.choices[0].message.content)
    print("=" * 60)
    print(
        f"\nToken使用: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}"
    )

except Exception as e:
    print(f"[FAIL] API call failed: {e}")
    import traceback

    traceback.print_exc()
