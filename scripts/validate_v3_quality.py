#!/usr/bin/env python3
"""
Quality Validation Report for Nelson Pediatrics V3 Dataset
"""

import pandas as pd
import re

def validate_dataset(csv_path):
    print("=" * 80)
    print("QUALITY VALIDATION REPORT - Nelson Pediatrics V3")
    print("=" * 80)
    
    df = pd.read_csv(csv_path)
    
    print(f"\n📊 Dataset Size: {len(df)} records")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    # 1. Missing Values Check
    print(f"\n✅ 1. Missing Values:")
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print("   ⭐⭐⭐⭐⭐ Zero missing values - Excellent!")
    else:
        print(f"   Missing values detected:\n{missing[missing > 0]}")
    
    # 2. Duplicate Rows Check
    print(f"\n✅ 2. Duplicate Rows:")
    duplicates = df.duplicated().sum()
    if duplicates == 0:
        print("   ⭐⭐⭐⭐⭐ Zero duplicate rows - Excellent!")
    else:
        print(f"   Found {duplicates} duplicate rows")
    
    # 3. Topic Name Length (Should be 2-4 words)
    print(f"\n✅ 3. Topic Name Quality:")
    topic_word_counts = df['topic_name'].apply(lambda x: len(str(x).split()))
    avg_topic_words = topic_word_counts.mean()
    max_topic_words = topic_word_counts.max()
    short_topics = (topic_word_counts <= 4).sum()
    
    print(f"   Average words: {avg_topic_words:.1f}")
    print(f"   Max words: {max_topic_words}")
    print(f"   Short topics (≤4 words): {short_topics}/{len(df)} ({short_topics/len(df)*100:.1f}%)")
    
    if avg_topic_words <= 4:
        print(f"   ⭐⭐⭐⭐⭐ Excellent! Topics are concise ({avg_topic_words:.1f} words avg)")
    elif avg_topic_words <= 6:
        print(f"   ⭐⭐⭐ Good, but could be shorter")
    else:
        print(f"   ⭐⭐ Needs improvement - topics too long")
    
    # 4. Summary Quality (Should be 3-5 sentences, 150-500 chars)
    print(f"\n✅ 4. Summary Quality:")
    summary_char_counts = df['summary'].apply(lambda x: len(str(x)))
    summary_sentence_counts = df['summary'].apply(lambda x: len(re.split(r'[.!?]+', str(x))))
    
    avg_summary_chars = summary_char_counts.mean()
    optimal_length = ((summary_char_counts >= 150) & (summary_char_counts <= 500)).sum()
    proper_sentences = ((summary_sentence_counts >= 3) & (summary_sentence_counts <= 6)).sum()
    
    print(f"   Average length: {avg_summary_chars:.0f} characters")
    print(f"   Optimal length (150-500 chars): {optimal_length}/{len(df)} ({optimal_length/len(df)*100:.1f}%)")
    print(f"   Proper sentence count (3-6): {proper_sentences}/{len(df)} ({proper_sentences/len(df)*100:.1f}%)")
    
    if optimal_length / len(df) >= 0.8:
        print(f"   ⭐⭐⭐⭐⭐ Excellent summary quality!")
    elif optimal_length / len(df) >= 0.6:
        print(f"   ⭐⭐⭐⭐ Good summary quality")
    else:
        print(f"   ⭐⭐⭐ Acceptable, room for improvement")
    
    # 5. Content Chunk Size (Should be 250-400 tokens ~= 1000-1600 chars)
    print(f"\n✅ 5. Content Chunk Size:")
    content_token_est = df['content'].apply(lambda x: len(str(x).split()))
    avg_content_tokens = content_token_est.mean()
    optimal_chunks = ((content_token_est >= 200) & (content_token_est <= 450)).sum()
    
    print(f"   Average tokens: {avg_content_tokens:.0f}")
    print(f"   Optimal size (200-450 tokens): {optimal_chunks}/{len(df)} ({optimal_chunks/len(df)*100:.1f}%)")
    
    if avg_content_tokens >= 250 and avg_content_tokens <= 400:
        print(f"   ⭐⭐⭐⭐⭐ Perfect semantic chunking!")
    else:
        print(f"   ⭐⭐⭐⭐ Good chunking")
    
    # 6. Text Cleaning Quality
    print(f"\n✅ 6. Text Cleaning Quality:")
    system_markers = df['content'].str.contains('>> CHAPTER:|Chapter \\d+ u', regex=True, na=False).sum()
    hyphenation_issues = df['content'].str.contains(r'\w+-\s*\n\s*\w+', regex=True, na=False).sum()
    
    if system_markers == 0 and hyphenation_issues == 0:
        print(f"   ⭐⭐⭐⭐⭐ Clean text - no system markers or hyphenation issues!")
    else:
        print(f"   System markers found: {system_markers}")
        print(f"   Hyphenation issues: {hyphenation_issues}")
    
    # 7. Category Distribution
    print(f"\n✅ 7. Category Distribution:")
    category_counts = df['category'].value_counts()
    print(f"   Unique categories: {df['category'].nunique()}")
    for cat, count in category_counts.head(5).items():
        print(f"   {cat}: {count} records")
    
    # 8. Overall Quality Score
    print(f"\n" + "=" * 80)
    print("OVERALL QUALITY ASSESSMENT")
    print("=" * 80)
    
    scores = {
        'Completeness': 5 if missing.sum() == 0 else 3,
        'Content Cleanliness': 5 if system_markers == 0 else 3,
        'Topic Coherence': 5 if avg_topic_words <= 4 else 3,
        'Summary Quality': 5 if optimal_length / len(df) >= 0.8 else 4,
        'RAG Suitability': 5 if avg_content_tokens >= 250 and avg_content_tokens <= 400 else 4
    }
    
    print(f"\n| Dimension            | Rating | Status |")
    print(f"|---------------------|--------|--------|")
    for dimension, score in scores.items():
        stars = '⭐' * score
        print(f"| {dimension:20} | {stars:10} | {'✓' if score >= 4 else '⚠️'} |")
    
    avg_score = sum(scores.values()) / len(scores)
    print(f"\n🎯 Average Score: {avg_score:.1f}/5.0")
    
    if avg_score >= 4.5:
        print("✅ PRODUCTION READY - Excellent quality!")
    elif avg_score >= 4.0:
        print("✅ HIGH QUALITY - Ready for RAG applications!")
    else:
        print("⚠️  NEEDS IMPROVEMENT")
    
    print("\n" + "=" * 80)
    
    # Sample Records
    print("\n📋 Sample Records (First 3):")
    for idx in range(min(3, len(df))):
        row = df.iloc[idx]
        print(f"\nRecord {idx+1}:")
        print(f"  Chapter: {row['chapter_number']} - {row['chapter_name']}")
        print(f"  Topic: {row['topic_name']}")
        print(f"  Category: {row['category']}")
        print(f"  Content tokens: {len(str(row['content']).split())}")
        print(f"  Summary: {str(row['summary'])[:200]}...")

if __name__ == '__main__':
    validate_dataset('nelson_pediatrics_dataset_v3_final.csv')
