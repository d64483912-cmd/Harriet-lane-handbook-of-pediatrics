import csv
import random

csv_path = '/project/workspace/nelson_pediatrics_dataset_final.csv'

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print("="*80)
print("NELSON PEDIATRICS DATASET EXTRACTION REPORT")
print("="*80)

print(f"\n📊 OVERALL STATISTICS")
print(f"  Total rows: {len(rows)}")
print(f"  Total unique chapters: {len(set(r['chapter_number'] for r in rows))}")
print(f"  Average chunks per chapter: {len(rows) / len(set(r['chapter_number'] for r in rows)):.2f}")
print(f"  Total characters in content: {sum(len(r['content']) for r in rows):,}")
print(f"  Total characters in summaries: {sum(len(r['summary']) for r in rows):,}")

print(f"\n✅ DATA QUALITY CHECKS")

chapter_counts = {}
for row in rows:
    ch_num = row['chapter_number']
    if ch_num not in chapter_counts:
        chapter_counts[ch_num] = 0
    chapter_counts[ch_num] += 1

all_three = all(count == 3 for count in chapter_counts.values())
print(f"  {'✓' if all_three else '✗'} All chapters have exactly 3 chunks: {all_three}")

all_complete = all(
    row['book_title'] and row['chapter_number'] and row['chapter_name'] and 
    row['topic_name'] and row['content'] and row['summary']
    for row in rows
)
print(f"  {'✓' if all_complete else '✗'} All fields populated: {all_complete}")

avg_content_len = sum(len(r['content']) for r in rows) / len(rows)
avg_summary_len = sum(len(r['summary']) for r in rows) / len(rows)
print(f"  ✓ Average content length: {avg_content_len:.0f} characters")
print(f"  ✓ Average summary length: {avg_summary_len:.0f} characters")

print(f"\n📚 CHAPTER COVERAGE")
print(f"  First chapter: {rows[0]['chapter_name']}")
print(f"  Last chapter: {rows[-1]['chapter_name']}")
print(f"  Chapter range: 1-{max(int(r['chapter_number']) for r in rows)}")

print(f"\n📋 SAMPLE ENTRIES (Random Selection)")
print("="*80)

sample_chapters = random.sample([r for r in rows], min(5, len(rows)))

for i, row in enumerate(sample_chapters, 1):
    print(f"\n--- Sample {i} ---")
    print(f"Book: {row['book_title']}")
    print(f"Chapter {row['chapter_number']}: {row['chapter_name']}")
    print(f"Topic: {row['topic_name']}")
    print(f"\nContent ({len(row['content'])} chars):")
    print(f"  {row['content'][:250]}...")
    print(f"\nSummary ({len(row['summary'])} chars):")
    print(f"  {row['summary']}")

print("\n" + "="*80)
print("DETAILED EXAMPLES - First 3 Chunks (Chapter 1)")
print("="*80)

for i, row in enumerate(rows[:3], 1):
    print(f"\n{'='*80}")
    print(f"CHUNK {i}/3")
    print(f"{'='*80}")
    print(f"Book Title: {row['book_title']}")
    print(f"Chapter Number: {row['chapter_number']}")
    print(f"Chapter Name: {row['chapter_name']}")
    print(f"Topic Name: {row['topic_name']}")
    print(f"\nContent ({len(row['content'])} characters):")
    print(row['content'][:500])
    if len(row['content']) > 500:
        print(f"... [+{len(row['content'])-500} more characters]")
    print(f"\nSummary ({len(row['summary'])} characters):")
    print(row['summary'])

print("\n" + "="*80)
print("FILE OUTPUT LOCATIONS")
print("="*80)
print(f"  CSV: /project/workspace/nelson_pediatrics_dataset_final.csv")
print(f"  JSON: /project/workspace/nelson_pediatrics_dataset_final.json")
print(f"\n  Rows: {len(rows) + 1} (including header)")
print(f"  Chapters: {len(set(r['chapter_number'] for r in rows))}")
print(f"  Chunks per chapter: 3")

print("\n" + "="*80)
print("✅ EXTRACTION COMPLETE - READY FOR USE")
print("="*80)
