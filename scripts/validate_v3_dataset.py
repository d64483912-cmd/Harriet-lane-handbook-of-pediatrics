#!/usr/bin/env python3
"""Validate V3 Dataset Quality"""

import csv

def validate_dataset():
    with open('dataset/nelson_pediatrics_dataset_v4_final.csv', 'r', encoding='utf-8') as f:
        records = list(csv.DictReader(f))
    
    print('='*70)
    print('V4 DATASET VALIDATION REPORT')
    print('='*70)
    
    # Record count validation
    total = len(records)
    target = 10455  # 697 chapters × 15 chunks
    print(f'\n📊 RECORD COUNT:')
    print(f'   Total Records: {total}')
    print(f'   Target: ~{target:,} (697 chapters × 15 chunks)')
    print(f'   Achievement: {total/target*100:.1f}%')
    print(f'   Status: {"❌ FAIL" if total < 8000 else "✅ PASS"}')
    
    # Token size validation
    token_counts = [len(r['content'].split()) for r in records[:200]]
    min_tokens = min(token_counts)
    max_tokens = max(token_counts)
    avg_tokens = sum(token_counts) / len(token_counts)
    in_range = sum(1 for t in token_counts if 250 <= t <= 400)
    
    print(f'\n📏 TOKEN SIZE (first 200 records):')
    print(f'   Min: {min_tokens} | Max: {max_tokens} | Avg: {avg_tokens:.0f}')
    print(f'   Target: 250-400 tokens')
    print(f'   In Range: {in_range}/{len(token_counts)} ({in_range/len(token_counts)*100:.1f}%)')
    print(f'   Status: {"❌ FAIL" if in_range/len(token_counts) < 0.6 else "✅ PASS"}')
    
    # Topic name validation
    topic_lengths = [len(r['topic_name']) for r in records[:100]]
    poor_topics = [r['topic_name'] for r in records[:20] if len(r['topic_name']) < 10 or len(r['topic_name']) > 50]
    
    print(f'\n🏷️  TOPIC NAMES (first 100 records):')
    print(f'   Min: {min(topic_lengths)} chars | Max: {max(topic_lengths)} chars')
    print(f'   Avg: {sum(topic_lengths)/len(topic_lengths):.1f} chars')
    print(f'   Poor Topics (first 20): {len(poor_topics)}')
    if poor_topics:
        for topic in poor_topics[:5]:
            print(f'      - "{topic}"')
    print(f'   Status: {"❌ FAIL" if len(poor_topics) > 5 else "✅ PASS"}')
    
    # Summary quality validation
    summary_lengths = [len(r['summary']) for r in records[:100]]
    
    print(f'\n📝 SUMMARY QUALITY (first 100 records):')
    print(f'   Min: {min(summary_lengths)} chars | Max: {max(summary_lengths)} chars')
    print(f'   Avg: {sum(summary_lengths)/len(summary_lengths):.0f} chars')
    print(f'   Target: 150-500 chars (3-5 sentences)')
    
    # Sample records
    print(f'\n📋 SAMPLE RECORDS:')
    for i in [0, 10, 50]:
        if i < len(records):
            r = records[i]
            tokens = len(r['content'].split())
            print(f'\n   Record {i+1}:')
            print(f'      Chapter: {r["chapter_number"]} - {r["chapter_name"][:40]}...')
            print(f'      Topic: {r["topic_name"][:50]}')
            print(f'      Tokens: {tokens}')
            print(f'      Summary: {r["summary"][:80]}...')
    
    # Overall assessment
    print(f'\n{"="*70}')
    print(f'OVERALL ASSESSMENT:')
    
    if total < 8000:
        print(f'❌ CRITICAL: Only {total} records generated (target: ~10,455)')
        print(f'   Issue: Chunking algorithm creating only ~1 chunk per chapter')
    elif avg_tokens > 600:
        print(f'❌ FAIL: Average chunk size {avg_tokens:.0f} tokens (target: 250-400)')
        print(f'   Issue: Chunks too large for RAG optimization')
    elif len(poor_topics) > 10:
        print(f'❌ FAIL: Too many poor quality topic names')
        print(f'   Issue: Topic extraction needs improvement')
    else:
        print(f'✅ PASS: Dataset meets quality requirements')
    
    print(f'{"="*70}\n')

if __name__ == '__main__':
    validate_dataset()
