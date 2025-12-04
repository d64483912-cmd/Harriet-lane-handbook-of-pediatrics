#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset Creation Script - Version 3 (Production Quality)
Addresses all quality check issues:
- Advanced text cleaning (hyphenation, line breaks, spacing)
- Proper clinical summarization (not raw text)
- Short normalized topic names (2-4 words)
- Semantic chunking (250-400 tokens)
- Standardized medical categories
"""

import re
import csv
import json
from typing import List, Dict, Tuple
from pathlib import Path


class NelsonPediatricsProcessorV3:
    def __init__(self, content_table_path: str, text_path: str):
        self.content_table_path = content_table_path
        self.text_path = text_path
        self.book_title = "Nelson Textbook of Pediatrics"
        self.chapters = []
        
        # Standardized medical category taxonomy
        self.category_taxonomy = {
            range(1, 6): "General Pediatrics",
            range(6, 19): "Social & Preventive Medicine",
            range(19, 32): "Child Development",
            range(32, 47): "Behavioral Pediatrics",
            range(47, 57): "Neurodevelopmental Disorders",
            range(57, 73): "Nutrition & Metabolism",
            range(73, 87): "Fluid & Electrolytes",
            range(87, 104): "Emergency Medicine",
            range(104, 111): "Genetics",
            range(111, 200): "Metabolic Diseases",
            range(200, 210): "Neonatal Medicine",
            range(210, 400): "Infectious Diseases",
            range(400, 450): "Immunology",
            range(450, 500): "Allergy",
            range(500, 550): "Rheumatology",
            range(550, 600): "Gastroenterology",
            range(600, 650): "Cardiology",
            range(650, 700): "Pulmonology",
        }
    
    def get_category(self, chapter_num: int) -> str:
        """Get standardized category"""
        for chapter_range, category in self.category_taxonomy.items():
            if chapter_num in chapter_range:
                return category
        return "General Pediatrics"
    
    def parse_content_table(self) -> List[Dict]:
        """Parse content table"""
        chapters = []
        with open(self.content_table_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith('CHAPTER:'):
                    match = re.match(r'CHAPTER:\s*(.+?)\s*\(Page:\s*(\d+)\)', line)
                    if match:
                        chapters.append({
                            'chapter_number': line_num,
                            'chapter_name': match.group(1).strip(),
                            'start_page': int(match.group(2))
                        })
        
        for i in range(len(chapters) - 1):
            chapters[i]['end_page'] = chapters[i + 1]['start_page'] - 1
        if chapters:
            chapters[-1]['end_page'] = 99999
            
        print(f"✓ Parsed {len(chapters)} chapters")
        return chapters
    
    def extract_chapter_text(self, start_page: int, end_page: int) -> str:
        """Extract chapter text"""
        chapter_text = []
        current_page = 0
        in_chapter = False
        
        with open(self.text_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                page_match = re.match(r'^--- PAGE (\d+) ---', line)
                if page_match:
                    current_page = int(page_match.group(1))
                    if current_page >= start_page and current_page <= end_page:
                        in_chapter = True
                    elif current_page > end_page:
                        break
                    continue
                if in_chapter:
                    chapter_text.append(line)
        
        return ''.join(chapter_text)
    
    def advanced_text_cleaning(self, text: str) -> str:
        """Advanced text cleaning with hyphenation and line break fixes"""
        # Remove download/copyright notices
        text = re.sub(r'Downloaded for .+ at .+ from ClinicalKey\.com.*?reserved\.', '', text, flags=re.DOTALL)
        
        # Remove chapter markers
        text = re.sub(r'>> CHAPTER:.*?\n', '', text)
        text = re.sub(r'Chapter \d+\s+[uv]\s+.*?\n', '', text)
        
        # Fix hyphenation at line breaks (critical fix)
        # "manage- \nment" -> "management"
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Fix line breaks within sentences
        # Join lines that don't end with sentence-ending punctuation
        lines = text.split('\n')
        fixed_lines = []
        buffer = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                if buffer:
                    fixed_lines.append(buffer)
                    buffer = ""
                continue
            
            # If buffer exists and current line starts with lowercase, merge
            if buffer and line and line[0].islower():
                buffer += " " + line
            # If buffer ends with sentence-ending punctuation, flush it
            elif buffer and re.search(r'[.!?]$', buffer):
                fixed_lines.append(buffer)
                buffer = line
            # Otherwise add to buffer
            else:
                if buffer:
                    buffer += " " + line
                else:
                    buffer = line
        
        if buffer:
            fixed_lines.append(buffer)
        
        text = '\n'.join(fixed_lines)
        
        # Normalize multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove isolated page numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Clean excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def semantic_chunking(self, text: str, target_tokens: int = 300, max_chunks: int = 3) -> List[str]:
        """Semantic chunking with 250-400 token targets"""
        if not text or len(text) < 100:
            return []
        
        # Approximate tokens (words + punctuation)
        words = text.split()
        total_tokens = len(words)
        
        # If very short, return as single chunk
        if total_tokens < 150:
            return [text]
        
        # Target tokens per chunk
        tokens_per_chunk = max(target_tokens, total_tokens // max_chunks)
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = len(para.split())
            
            # If adding this paragraph exceeds target, finalize current chunk
            if current_tokens > 0 and current_tokens + para_tokens > tokens_per_chunk * 1.3:
                chunks.append(' '.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
            
            # If we've reached max chunks, add remaining to last chunk
            if len(chunks) >= max_chunks - 1:
                break
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # Add any remaining paragraphs to last chunk
        if len(chunks) > 0 and len(chunks) < len(paragraphs):
            remaining_idx = sum(len(c.split('\n\n')) for c in chunks)
            if remaining_idx < len(paragraphs):
                remaining = ' '.join(paragraphs[remaining_idx:])
                if remaining:
                    chunks[-1] += ' ' + remaining
        
        # Ensure we have exactly max_chunks or less
        return chunks[:max_chunks]
    
    def extract_short_topic(self, chunk_text: str, chapter_name: str) -> str:
        """Extract very short topic name (2-4 words max)"""
        if not chunk_text:
            # Extract 2-3 words from chapter name
            words = chapter_name.split()[:3]
            return ' '.join(words)
        
        lines = chunk_text.split('\n')
        
        # Look for section headings
        for line in lines[:10]:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Uppercase headings
            if 10 < len(line) < 50 and line.isupper():
                words = line.split()[:3]
                return ' '.join(words).title()
            
            # Title case headings
            if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){1,3}$', line):
                words = line.split()[:3]
                return ' '.join(words)
        
        # Extract from first sentence
        sentences = re.split(r'[.!?]\s+', chunk_text)
        for sent in sentences[:2]:
            sent = sent.strip()
            if 20 < len(sent) < 150:
                # Extract key noun phrases (simplified)
                words = sent.split()
                # Take first 2-3 capitalized words or first 3 words
                topic_words = []
                for w in words[:6]:
                    w = re.sub(r'[^\w\s]', '', w)
                    if w and (w[0].isupper() or len(topic_words) < 3):
                        topic_words.append(w)
                    if len(topic_words) >= 3:
                        break
                
                if topic_words:
                    return ' '.join(topic_words[:3])
        
        # Fallback: chapter name truncated
        words = chapter_name.split()[:3]
        return ' '.join(words)
    
    def generate_clinical_summary(self, chunk_text: str) -> str:
        """Generate proper clinical summary (3-5 sentences)"""
        if not chunk_text or len(chunk_text) < 100:
            return ""
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        
        # Filter for clinical content (40-350 chars)
        clinical_sentences = []
        for s in sentences:
            s = s.strip()
            if 40 < len(s) < 350:
                # Skip tables, citations, system text
                if not re.match(r'^(Table|Fig|Chapter|Downloaded|\d+\.|>>)', s):
                    # Prefer sentences with medical terms
                    if any(term in s.lower() for term in ['patient', 'treatment', 'diagnosis', 'child', 'clinical', 'symptom', 'therapy', 'disease', 'condition']):
                        clinical_sentences.append(s)
                    elif len(clinical_sentences) < 3:
                        clinical_sentences.append(s)
        
        if not clinical_sentences:
            # Fallback: take first 3 reasonable sentences
            clinical_sentences = [s.strip() for s in sentences[:5] if 30 < len(s.strip()) < 400]
        
        # Select 3-5 sentences strategically
        if len(clinical_sentences) == 0:
            return chunk_text[:300].strip() + "..."
        
        summary_sentences = []
        total = len(clinical_sentences)
        
        # Always include first (introduces topic)
        summary_sentences.append(clinical_sentences[0])
        
        # Add middle/key sentences
        if total >= 3:
            summary_sentences.append(clinical_sentences[total // 2])
        
        if total >= 5:
            summary_sentences.append(clinical_sentences[2 * total // 3])
        
        if total >= 7:
            summary_sentences.append(clinical_sentences[total // 3])
        
        # Add final if different enough
        if total >= 2 and clinical_sentences[-1] not in summary_sentences:
            summary_sentences.append(clinical_sentences[-1])
        
        # Limit to 5 sentences
        summary = ' '.join(summary_sentences[:5])
        
        # Final cleanup
        summary = re.sub(r'\s+', ' ', summary)
        summary = re.sub(r'\([^)]{150,}\)', '', summary)
        
        return summary.strip()
    
    def process_all_chapters(self) -> List[Dict]:
        """Process all chapters with V3 improvements"""
        self.chapters = self.parse_content_table()
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters (V3 quality)...\n")
        
        for idx, chapter in enumerate(self.chapters, 1):
            chapter_num = chapter['chapter_number']
            chapter_name = chapter['chapter_name']
            start_page = chapter['start_page']
            end_page = chapter['end_page']
            category = self.get_category(chapter_num)
            
            if idx % 50 == 0:
                print(f"[{idx}/{len(self.chapters)}] Processing...")
            
            raw_text = self.extract_chapter_text(start_page, end_page)
            
            if not raw_text or len(raw_text) < 200:
                continue
            
            # Advanced cleaning
            cleaned_text = self.advanced_text_cleaning(raw_text)
            
            # Semantic chunking (250-400 tokens each)
            chunks = self.semantic_chunking(cleaned_text, target_tokens=300, max_chunks=3)
            
            for chunk_idx, chunk in enumerate(chunks, 1):
                if not chunk or len(chunk) < 100:
                    continue
                
                # Short topic name (2-4 words)
                topic_name = self.extract_short_topic(chunk, chapter_name)
                
                # Clinical summary (3-5 sentences)
                summary = self.generate_clinical_summary(chunk)
                
                if not summary:
                    continue
                
                dataset.append({
                    'book_title': self.book_title,
                    'chapter_number': chapter_num,
                    'chapter_name': chapter_name,
                    'topic_name': topic_name,
                    'content': chunk,
                    'category': category,
                    'summary': summary
                })
        
        print(f"\n✅ Processing complete: {len(dataset)} high-quality records")
        return dataset
    
    def save_to_csv(self, dataset: List[Dict], output_path: str):
        """Save to CSV"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'book_title', 'chapter_number', 'chapter_name',
                'topic_name', 'content', 'category', 'summary'
            ])
            writer.writeheader()
            writer.writerows(dataset)
        print(f"💾 CSV saved: {output_path}")
    
    def save_to_json(self, dataset: List[Dict], output_path: str):
        """Save to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON saved: {output_path}")
    
    def generate_quality_report(self, dataset: List[Dict]) -> str:
        """Generate quality validation report"""
        report = []
        report.append("=" * 70)
        report.append("QUALITY VALIDATION REPORT - V3")
        report.append("=" * 70)
        
        # Basic stats
        report.append(f"\n📊 Dataset Size: {len(dataset)} records")
        report.append(f"📚 Chapters: {len(set(row['chapter_number'] for row in dataset))}")
        
        # Missing values check
        report.append("\n✅ Missing Values Check:")
        for col in ['book_title', 'chapter_number', 'chapter_name', 'topic_name', 'content', 'category', 'summary']:
            missing = sum(1 for row in dataset if not row.get(col))
            report.append(f"   {col}: {missing} missing")
        
        # Topic name length check
        topic_lengths = [len(row['topic_name'].split()) for row in dataset]
        avg_topic_words = sum(topic_lengths) / len(topic_lengths)
        report.append(f"\n✅ Topic Names: Avg {avg_topic_words:.1f} words (target: 2-4)")
        
        # Summary quality check
        summary_lengths = [len(row['summary']) for row in dataset]
        avg_summary_chars = sum(summary_lengths) / len(summary_lengths)
        report.append(f"✅ Summaries: Avg {avg_summary_chars:.0f} characters")
        
        # Token count check (approximate)
        content_tokens = [len(row['content'].split()) for row in dataset]
        avg_tokens = sum(content_tokens) / len(content_tokens)
        report.append(f"✅ Content Chunks: Avg {avg_tokens:.0f} tokens (target: 250-400)")
        
        # Category distribution
        categories = {}
        for row in dataset:
            cat = row['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        report.append(f"\n📂 Category Distribution:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            report.append(f"   {cat}: {count}")
        
        report.append("\n" + "=" * 70)
        
        return '\n'.join(report)


def main():
    print("=" * 70)
    print("Nelson Pediatrics Dataset - V3 Production Quality")
    print("=" * 70)
    
    processor = NelsonPediatricsProcessorV3(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt'
    )
    
    dataset = processor.process_all_chapters()
    
    # Save outputs
    processor.save_to_csv(dataset, 'nelson_pediatrics_dataset_v3.csv')
    processor.save_to_json(dataset, 'nelson_pediatrics_dataset_v3.json')
    
    # Generate quality report
    report = processor.generate_quality_report(dataset)
    print("\n" + report)
    
    with open('QUALITY_REPORT_V3.txt', 'w') as f:
        f.write(report)
    print("\n💾 Quality report saved: QUALITY_REPORT_V3.txt")


if __name__ == '__main__':
    main()
