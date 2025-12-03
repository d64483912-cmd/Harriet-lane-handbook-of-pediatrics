import csv
import json

csv_path = '/project/workspace/nelson_pediatrics_dataset.csv'

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows: {len(rows)}")
print(f"Total chapters (rows/3): {len(rows)/3:.0f}")
print("\n" + "="*80)
print("Sample rows from the dataset:")
print("="*80)

for i, row in enumerate(rows[:6], 1):
    print(f"\nRow {i}:")
    print(f"  Book Title: {row['book_title']}")
    print(f"  Chapter Number: {row['chapter_number']}")
    print(f"  Chapter Name: {row['chapter_name']}")
    print(f"  Topic Name: {row['topic_name']}")
    print(f"  Content Length: {len(row['content'])} chars")
    print(f"  Content Preview: {row['content'][:200]}...")
    print(f"  Summary Length: {len(row['summary'])} chars")
    print(f"  Summary: {row['summary'][:300]}...")

print("\n" + "="*80)
print("Verification of 3 chunks per chapter:")
print("="*80)

chapter_counts = {}
for row in rows:
    ch_num = row['chapter_number']
    if ch_num not in chapter_counts:
        chapter_counts[ch_num] = []
    chapter_counts[ch_num].append(row['topic_name'])

print(f"\nTotal unique chapters: {len(chapter_counts)}")

non_three = []
for ch_num, topics in chapter_counts.items():
    if len(topics) != 3:
        non_three.append((ch_num, len(topics)))

if non_three:
    print(f"\nChapters with != 3 chunks: {len(non_three)}")
    for ch_num, count in non_three[:10]:
        print(f"  Chapter {ch_num}: {count} chunks")
else:
    print("\n✓ All chapters have exactly 3 chunks!")

print("\n" + "="*80)
print("Column completeness check:")
print("="*80)

empty_fields = {
    'book_title': 0,
    'chapter_number': 0,
    'chapter_name': 0,
    'topic_name': 0,
    'content': 0,
    'summary': 0
}

for row in rows:
    for field in empty_fields:
        if not row[field] or len(row[field].strip()) == 0:
            empty_fields[field] += 1

for field, count in empty_fields.items():
    status = "✓" if count == 0 else "✗"
    print(f"{status} {field}: {count} empty fields")

print("\n" + "="*80)
print("Sample from middle of dataset (Chapter 100):")
print("="*80)

for row in rows:
    if row['chapter_number'] == '100':
        print(f"\nChapter: {row['chapter_name']}")
        print(f"Topic: {row['topic_name']}")
        print(f"Content: {row['content'][:300]}...")
        print(f"Summary: {row['summary'][:250]}...")
        break
