#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset Creation Script - Version 2 (Production Quality)
Fixed issues:
- Removed system markers and chapter headers from content
- Improved summary generation (no defaults)
- Normalized topic names to short labels
- Added category column
- Better text cleaning
"""

import re
import csv
import json
from typing import List, Dict, Tuple
from pathlib import Path


class NelsonPediatricsProcessorV2:
    def __init__(self, content_table_path: str, text_path: str):
        self.content_table_path = content_table_path
        self.text_path = text_path
        self.book_title = "Nelson Textbook of Pediatrics"
        self.chapters = []
        self.chapter_texts = {}
        
        # Category mapping based on chapter ranges (approximate)
        self.category_map = {
            range(1, 20): "Child Health & Social Issues",
            range(20, 32): "Growth & Development",
            range(32, 57): "Behavioral & Mental Health",
            range(57, 73): "Nutrition & Metabolic",
            range(73, 87): "Fluid & Electrolyte",
            range(87, 99): "Emergency & Critical Care",
            range(99, 103): "Pain & Anesthesia",
            range(103, 111): "Genetics & Genomics",
            range(111, 140): "Metabolic Disorders",
            range(140, 200): "Fetal & Neonatal Medicine",
            range(200, 300): "Infectious Diseases",
            range(300, 400): "Immunology & Allergy",
            range(400, 500): "Gastroenterology",
            range(500, 600): "Cardiology",
            range(600, 650): "Respiratory Diseases",
            range(650, 700): "Laboratory & Reference",
        }
        
    def get_category(self, chapter_num: int) -> str:
        """Determine category based on chapter number"""
        for chapter_range, category in self.category_map.items():
            if chapter_num in chapter_range:
                return category
        return "General Pediatrics"
    
    def parse_content_table(self) -> List[Dict]:
        """Parse the content table to extract chapter metadata"""
        chapters = []
        
        with open(self.content_table_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith('CHAPTER:'):
                    match = re.match(r'CHAPTER:\s*(.+?)\s*\(Page:\s*(\d+)\)', line)
                    if match:
                        chapter_name = match.group(1).strip()
                        page_num = int(match.group(2))
                        
                        chapters.append({
                            'chapter_number': line_num,
                            'chapter_name': chapter_name,
                            'start_page': page_num
                        })
        
        for i in range(len(chapters) - 1):
            chapters[i]['end_page'] = chapters[i + 1]['start_page'] - 1
        
        if chapters:
            chapters[-1]['end_page'] = 99999
            
        print(f"✓ Parsed {len(chapters)} chapters from content table")
        return chapters
    
    def extract_chapter_text(self, start_page: int, end_page: int) -> str:
        """Extract text for a specific chapter based on page range"""
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
    
    def clean_text(self, text: str, remove_chapter_markers: bool = True) -> str:
        """Enhanced text cleaning with removal of system markers"""
        # Remove download/copyright notices
        text = re.sub(r'Downloaded for .+ at .+ from ClinicalKey\.com.*?reserved\.', '', text, flags=re.DOTALL)
        
        # Remove chapter markers and system annotations
        if remove_chapter_markers:
            text = re.sub(r'>> CHAPTER:.*?\n', '', text)
            text = re.sub(r'Chapter \d+\s+[uv]\s+.*?\n', '', text)
        
        # Remove line-break hyphenation
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Clean up spaces
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove isolated page numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def split_into_chunks(self, text: str, num_chunks: int = 3) -> List[str]:
        """Split chapter text into N logically meaningful chunks"""
        if not text or len(text) < 100:
            return [""] * num_chunks
        
        lines = text.split('\n')
        section_indices = [0]
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Better heuristics for section headings
            if line and 10 < len(line) < 80:
                if line.isupper() and len(line) > 10:
                    section_indices.append(i)
                elif re.match(r'^[A-Z][A-Za-z\s]{10,70}$', line) and i > 0:
                    if not lines[i-1].strip():
                        section_indices.append(i)
        
        section_indices.append(len(lines))
        
        if len(section_indices) > 4:
            sections_per_chunk = len(section_indices) // (num_chunks + 1)
            chunk_boundaries = [
                section_indices[0],
                section_indices[sections_per_chunk] if sections_per_chunk < len(section_indices) else len(lines) // 3,
                section_indices[2 * sections_per_chunk] if 2 * sections_per_chunk < len(section_indices) else 2 * len(lines) // 3,
                len(lines)
            ]
        else:
            chunk_size = len(lines) // num_chunks
            chunk_boundaries = [i * chunk_size for i in range(num_chunks)] + [len(lines)]
        
        chunks = []
        for i in range(num_chunks):
            start_idx = chunk_boundaries[i]
            end_idx = chunk_boundaries[i + 1] if i + 1 < len(chunk_boundaries) else len(lines)
            chunk_text = '\n'.join(lines[start_idx:end_idx])
            chunks.append(self.clean_text(chunk_text, remove_chapter_markers=True))
        
        return chunks
    
    def extract_topic_name(self, chunk_text: str, chapter_name: str) -> str:
        """Extract normalized topic name (1-5 words)"""
        if not chunk_text:
            return chapter_name
        
        lines = chunk_text.split('\n')
        
        for line in lines[:15]:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Check for heading patterns
            if 10 < len(line) < 80:
                # All caps heading
                if line.isupper():
                    # Normalize: take first 5 words max
                    words = line.split()[:5]
                    return ' '.join(words).title()
                
                # Title case heading
                if re.match(r'^[A-Z][A-Za-z\s\-,]{10,70}$', line):
                    words = line.split()[:5]
                    return ' '.join(words)
        
        # Fallback: extract first meaningful phrase from content
        sentences = re.split(r'[.!?]\s+', chunk_text)
        for sent in sentences[:3]:
            if 20 < len(sent) < 100:
                words = sent.strip().split()[:5]
                topic = ' '.join(words)
                # Clean up
                topic = re.sub(r'[^\w\s\-]', '', topic)
                if len(topic) > 10:
                    return topic.title()
        
        return chapter_name
    
    def generate_summary(self, chunk_text: str, min_length: int = 200) -> str:
        """Generate improved clinical summary - no defaults"""
        if not chunk_text or len(chunk_text) < min_length:
            # Try to extract whatever is available
            if chunk_text:
                return chunk_text[:200].strip() + "..."
            return ""
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        
        # Filter valid medical sentences
        valid_sentences = []
        for s in sentences:
            s = s.strip()
            # Skip very short, very long, or system messages
            if 40 < len(s) < 400:
                if not s.startswith('Downloaded'):
                    if not re.match(r'^(Chapter|>>|Table|Fig)', s):
                        valid_sentences.append(s)
        
        if not valid_sentences:
            # Extract first paragraph
            paragraphs = chunk_text.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if len(para) > 100:
                    return para[:250].strip() + "..."
            return chunk_text[:200].strip() + "..."
        
        # Smart selection: beginning, key middle points, clinical relevance
        summary_sentences = []
        total = len(valid_sentences)
        
        if total > 0:
            # First sentence (usually introduces topic)
            summary_sentences.append(valid_sentences[0])
            
            if total > 3:
                # Add 2-3 more sentences from strategic positions
                summary_sentences.append(valid_sentences[total // 3])
                
            if total > 5:
                summary_sentences.append(valid_sentences[total // 2])
                
            if total > 8:
                summary_sentences.append(valid_sentences[2 * total // 3])
        
        summary = ' '.join(summary_sentences[:5])
        
        # Final cleanup
        summary = re.sub(r'\s+', ' ', summary)
        summary = re.sub(r'\([^)]{150,}\)', '', summary)
        
        return summary.strip() if summary else chunk_text[:250].strip() + "..."
    
    def process_all_chapters(self) -> List[Dict]:
        """Process all chapters and generate enhanced dataset"""
        self.chapters = self.parse_content_table()
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters...")
        
        for idx, chapter in enumerate(self.chapters, 1):
            chapter_num = chapter['chapter_number']
            chapter_name = chapter['chapter_name']
            start_page = chapter['start_page']
            end_page = chapter['end_page']
            category = self.get_category(chapter_num)
            
            print(f"\n[{idx}/{len(self.chapters)}] Chapter {chapter_num}: {chapter_name}")
            print(f"   Category: {category}")
            print(f"   Pages {start_page}-{end_page}")
            
            raw_text = self.extract_chapter_text(start_page, end_page)
            
            if not raw_text or len(raw_text) < 100:
                print(f"   ⚠️  Warning: Minimal content found, skipping")
                continue
            
            cleaned_text = self.clean_text(raw_text, remove_chapter_markers=False)
            chunks = self.split_into_chunks(cleaned_text, num_chunks=3)
            
            for chunk_idx, chunk in enumerate(chunks, 1):
                if not chunk or len(chunk) < 50:
                    continue
                    
                topic_name = self.extract_topic_name(chunk, chapter_name)
                summary = self.generate_summary(chunk)
                
                dataset.append({
                    'book_title': self.book_title,
                    'chapter_number': chapter_num,
                    'chapter_name': chapter_name,
                    'topic_name': topic_name,
                    'content': chunk,
                    'category': category,
                    'summary': summary
                })
                
                print(f"   ✓ Chunk {chunk_idx}/3: {len(chunk)} chars, topic: {topic_name[:40]}...")
        
        print(f"\n✅ Processing complete: {len(dataset)} total rows")
        return dataset
    
    def save_to_csv(self, dataset: List[Dict], output_path: str):
        """Save dataset to CSV file"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'book_title', 'chapter_number', 'chapter_name', 
                'topic_name', 'content', 'category', 'summary'
            ])
            writer.writeheader()
            writer.writerows(dataset)
        print(f"\n💾 Saved CSV: {output_path}")
    
    def save_to_json(self, dataset: List[Dict], output_path: str):
        """Save dataset to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved JSON: {output_path}")


def main():
    print("=" * 70)
    print("Nelson Pediatrics Dataset Creation Tool - Version 2")
    print("Production Quality with Enhanced Cleaning")
    print("=" * 70)
    
    processor = NelsonPediatricsProcessorV2(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt'
    )
    
    dataset = processor.process_all_chapters()
    
    processor.save_to_csv(dataset, 'nelson_pediatrics_dataset_v2.csv')
    processor.save_to_json(dataset, 'nelson_pediatrics_dataset_v2.json')
    
    # Statistics
    print("\n" + "=" * 70)
    print("📈 DATASET STATISTICS")
    print("=" * 70)
    print(f"Total rows: {len(dataset)}")
    print(f"Total chapters: {len(set(row['chapter_number'] for row in dataset))}")
    print(f"Average chunks per chapter: {len(dataset) / len(set(row['chapter_number'] for row in dataset)):.1f}")
    
    # Category distribution
    categories = {}
    for row in dataset:
        cat = row['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count} chunks")
    
    print("\n✅ Dataset creation complete!")


if __name__ == '__main__':
    main()
