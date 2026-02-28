#!/usr/bin/env python3
"""Test DeepSeek API key directly using OpenAI SDK - Save output to file"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
print(f"API Key loaded: {api_key[:25]}..." if api_key else "NOT SET")

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

print("Calling DeepSeek API...")

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

content = response.choices[0].message.content

# Save to file to avoid encoding issues
output_file = "test_output.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"[OK] Response saved to {output_file}")
print(
    f"Token usage: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}"
)

# Also print first 100 chars
print(f"Preview: {content[:100]}...")
