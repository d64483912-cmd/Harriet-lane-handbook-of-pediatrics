#!/usr/bin/env python3
"""
Quick sample viewer for Nelson Pediatrics dataset
"""

import csv
import json

def view_csv_sample():
    """Display first few rows from CSV"""
    print("=" * 80)
    print("CSV SAMPLE - First 3 Rows")
    print("=" * 80)
    
    with open('nelson_pediatrics_dataset.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 3:
                break
            print(f"\n[Row {i+1}]")
            print(f"Book: {row['book_title']}")
            print(f"Chapter: #{row['chapter_number']} - {row['chapter_name']}")
            print(f"Topic: {row['topic_name'][:80]}...")
            print(f"Content length: {len(row['content'])} characters")
            print(f"Summary: {row['summary'][:150]}...")
    
    print("\n" + "=" * 80)

def view_stats():
    """Display dataset statistics"""
    print("\n" + "=" * 80)
    print("DATASET STATISTICS")
    print("=" * 80)
    
    # Count lines in CSV
    with open('nelson_pediatrics_dataset.csv', 'r', encoding='utf-8') as f:
        csv_lines = sum(1 for _ in f)
    
    # Load JSON
    with open('nelson_pediatrics_dataset.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    total_rows = len(json_data)
    total_chapters = total_rows // 3
    
    # Calculate content statistics
    total_content_chars = sum(len(row['content']) for row in json_data)
    avg_content_per_chunk = total_content_chars // total_rows
    
    print(f"Total rows: {total_rows}")
    print(f"Total chapters: {total_chapters}")
    print(f"Chunks per chapter: 3")
    print(f"CSV file lines: {csv_lines} (includes header)")
    print(f"Average content per chunk: {avg_content_per_chunk} characters")
    print(f"Total content size: {total_content_chars:,} characters")
    
    # Show chapter distribution
    chapters = set(row['chapter_number'] for row in json_data)
    print(f"\nChapter numbers range: {min(chapters)} to {max(chapters)}")
    print(f"Unique chapters: {len(chapters)}")
    
    print("=" * 80)

if __name__ == '__main__':
    view_stats()
    view_csv_sample()
