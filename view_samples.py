import csv
import sys

csv_path = '/project/workspace/nelson_pediatrics_dataset_final.csv'

def display_chapter(chapter_num):
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r['chapter_number'] == str(chapter_num)]
    
    if not rows:
        print(f"Chapter {chapter_num} not found!")
        return
    
    print("="*80)
    print(f"CHAPTER {chapter_num}: {rows[0]['chapter_name']}")
    print("="*80)
    
    for i, row in enumerate(rows, 1):
        print(f"\n{'─'*80}")
        print(f"CHUNK {i}/3: {row['topic_name']}")
        print(f"{'─'*80}")
        print(f"\n📄 Content ({len(row['content'])} characters):")
        print(f"{row['content'][:400]}...")
        print(f"\n📋 Summary ({len(row['summary'])} characters):")
        print(f"{row['summary']}")
        print()

def display_random_chapters(count=3):
    import random
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    chapters = {}
    for row in rows:
        ch_num = int(row['chapter_number'])
        if ch_num not in chapters:
            chapters[ch_num] = []
        chapters[ch_num].append(row)
    
    selected = random.sample(list(chapters.keys()), min(count, len(chapters)))
    
    for ch_num in selected:
        print("\n" + "="*80)
        print(f"CHAPTER {ch_num}: {chapters[ch_num][0]['chapter_name']}")
        print("="*80)
        
        for i, row in enumerate(chapters[ch_num], 1):
            print(f"\n  Chunk {i}/3: {row['topic_name']}")
            print(f"  Content: {len(row['content'])} chars")
            print(f"  Summary: {row['summary'][:150]}...")
            print()

def search_topic(keyword):
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        matches = [r for r in reader if keyword.lower() in r['chapter_name'].lower() or 
                   keyword.lower() in r['topic_name'].lower()]
    
    print(f"\n🔍 Found {len(matches)} matches for '{keyword}':")
    print("="*80)
    
    for row in matches[:10]:
        print(f"\nChapter {row['chapter_number']}: {row['chapter_name']}")
        print(f"  Topic: {row['topic_name']}")
        print(f"  Summary: {row['summary'][:200]}...")
        print()
    
    if len(matches) > 10:
        print(f"\n... and {len(matches)-10} more results")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'search' and len(sys.argv) > 2:
            search_topic(sys.argv[2])
        elif sys.argv[1] == 'random':
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            display_random_chapters(count)
        else:
            try:
                chapter_num = int(sys.argv[1])
                display_chapter(chapter_num)
            except ValueError:
                print("Usage: python3 view_samples.py [chapter_number|'random' [count]|'search' keyword]")
    else:
        print("Nelson Pediatrics Dataset Viewer")
        print("="*80)
        print("\nUsage:")
        print("  python3 view_samples.py 1              # View chapter 1")
        print("  python3 view_samples.py random 5       # View 5 random chapters")
        print("  python3 view_samples.py search cardiac # Search for 'cardiac'")
        print("\nShowing 3 random chapters as demo:")
        display_random_chapters(3)
