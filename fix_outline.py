"""Fix truncated outline JSON and prepare for writing."""
import json
from pathlib import Path

outline_dir = Path('data/novels/qiewei_v2/outline')

# 1. 读取并修复 full_outline_raw.json
with open(outline_dir / 'full_outline_raw.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

content = raw_data.get('raw_outline', '').strip()
if content.startswith('```json'): content = content[7:]
if content.endswith('```'): content = content[:-3]
content = content.strip()

# 找到截断前的有效 JSON
# 简单方法：不断截断直到能解析
for cut_pos in range(len(content), 0, -100):
    try:
        outline = json.loads(content[:cut_pos])
        print(f"修复成功！截断位置：{cut_pos}")
        break
    except:
        continue
else:
    print("无法修复，使用原始 5 章大纲")
    outline = None

if outline:
    with open(outline_dir / 'full_outline_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)
    print(f"已保存 full_outline_fixed.json")
    print(f"title: {outline.get('title')}")
    print(f"volumes: {len(outline.get('volumes', []))}")

# 2. 读取已有的 5 章详细大纲
with open(outline_dir / 'outline.json', 'r', encoding='utf-8') as f:
    ch5_outline = json.load(f)

print(f"\n已有 5 章详细大纲")
print(f"  Ch1: {ch5_outline['volumes'][0]['chapters'][0]['title']}")

# 3. 合并为一个可用的 outline 文件
merged = {
    "title": "窃魏",
    "total_chapters": 500,
    "volumes": outline.get('volumes', []) if outline else [
        {"volume_number": 1, "title": "卷一：猎户惊龙", "chapter_range": [1, 80], "summary": "李曜穿越成猎户，救公主，投尔朱荣"}
    ],
    "volume1_chapters": ch5_outline.get('volumes', [{}])[0].get('chapters', [])
}

with open(outline_dir / 'outline_ready.json', 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f"\n已保存 outline_ready.json (可直接用于写作)")
print(f"  第一卷详细章节：{len(merged['volume1_chapters'])} 章")
