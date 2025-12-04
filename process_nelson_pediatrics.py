#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset Creation Script
Extracts structured, clinically accurate data from nelson_pediatrics.txt
using chapter structure from nelson_pediatrics_content_table.txt
"""

import re
import csv
import json
from typing import List, Dict, Tuple
from pathlib import Path


class NelsonPediatricsProcessor:
    def __init__(self, content_table_path: str, text_path: str):
        self.content_table_path = content_table_path
        self.text_path = text_path
        self.book_title = "Nelson Textbook of Pediatrics"
        self.chapters = []
        self.chapter_texts = {}
        
    def parse_content_table(self) -> List[Dict]:
        """Parse the content table to extract chapter metadata"""
        chapters = []
        
        with open(self.content_table_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith('CHAPTER:'):
                    # Extract chapter name and page number
                    # Format: CHAPTER: Name (Page: XXX)
                    match = re.match(r'CHAPTER:\s*(.+?)\s*\(Page:\s*(\d+)\)', line)
                    if match:
                        chapter_name = match.group(1).strip()
                        page_num = int(match.group(2))
                        
                        chapters.append({
                            'chapter_number': line_num,
                            'chapter_name': chapter_name,
                            'start_page': page_num
                        })
        
        # Calculate end pages for each chapter
        for i in range(len(chapters) - 1):
            chapters[i]['end_page'] = chapters[i + 1]['start_page'] - 1
        
        # Last chapter goes to the end
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
                # Check for page markers
                page_match = re.match(r'^--- PAGE (\d+) ---', line)
                if page_match:
                    current_page = int(page_match.group(1))
                    
                    # Check if we've entered the chapter range
                    if current_page >= start_page and current_page <= end_page:
                        in_chapter = True
                    elif current_page > end_page:
                        break
                    continue
                
                # Collect text if we're in the chapter
                if in_chapter:
                    chapter_text.append(line)
        
        return ''.join(chapter_text)
    
    def clean_text(self, text: str) -> str:
        """Clean the extracted text by removing artifacts"""
        # Remove download/copyright notices
        text = re.sub(r'Downloaded for .+ at .+ from ClinicalKey\.com.*?reserved\.', '', text, flags=re.DOTALL)
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove line-break hyphenation (word- \nword -> word)
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Clean up spaces
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove isolated page numbers (lines with just numbers)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def split_into_chunks(self, text: str, num_chunks: int = 3) -> List[str]:
        """Split chapter text into N logically meaningful chunks"""
        if not text:
            return [""] * num_chunks
        
        # First, try to split by major section headings
        # Look for lines that are likely headings (short, capitalized, etc.)
        lines = text.split('\n')
        
        # Find potential section breaks
        section_indices = [0]
        for i, line in enumerate(lines):
            line = line.strip()
            # Heuristics for section headings
            if line and len(line) < 100 and line.isupper() and len(line) > 5:
                section_indices.append(i)
            elif re.match(r'^[A-Z][A-Za-z\s]{10,80}$', line) and i > 0:
                # Title case lines that look like headings
                if not lines[i-1].strip():  # Preceded by blank line
                    section_indices.append(i)
        
        section_indices.append(len(lines))
        
        # If we have enough sections, group them into chunks
        if len(section_indices) > 4:
            # Distribute sections evenly across chunks
            sections_per_chunk = len(section_indices) // (num_chunks + 1)
            chunk_boundaries = [
                section_indices[0],
                section_indices[sections_per_chunk] if sections_per_chunk < len(section_indices) else len(lines) // 3,
                section_indices[2 * sections_per_chunk] if 2 * sections_per_chunk < len(section_indices) else 2 * len(lines) // 3,
                len(lines)
            ]
        else:
            # Fall back to equal division
            chunk_size = len(lines) // num_chunks
            chunk_boundaries = [i * chunk_size for i in range(num_chunks)] + [len(lines)]
        
        # Create chunks
        chunks = []
        for i in range(num_chunks):
            start_idx = chunk_boundaries[i]
            end_idx = chunk_boundaries[i + 1] if i + 1 < len(chunk_boundaries) else len(lines)
            chunk_text = '\n'.join(lines[start_idx:end_idx])
            chunks.append(self.clean_text(chunk_text))
        
        return chunks
    
    def extract_topic_name(self, chunk_text: str, chapter_name: str) -> str:
        """Extract topic name from chunk text"""
        if not chunk_text:
            return chapter_name
        
        lines = chunk_text.split('\n')
        
        # Look for the first substantial heading or section title
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if not line:
                continue
            
            # Check for heading patterns
            if 5 < len(line) < 100:
                # All caps heading
                if line.isupper():
                    return line.title()
                
                # Title case heading
                if re.match(r'^[A-Z][A-Za-z\s\-,]{5,80}$', line):
                    return line
        
        # If no clear topic found, use chapter name
        return chapter_name
    
    def generate_summary(self, chunk_text: str, max_sentences: int = 5) -> str:
        """Generate a clinical summary from chunk text"""
        if not chunk_text or len(chunk_text) < 100:
            return "Content not available for summary."
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        
        # Filter out very short or very long sentences
        valid_sentences = [
            s.strip() for s in sentences 
            if 50 < len(s.strip()) < 500 and not s.strip().startswith('Downloaded')
        ]
        
        if not valid_sentences:
            # Fall back to taking first few sentences
            valid_sentences = [s.strip() for s in sentences[:10] if len(s.strip()) > 30]
        
        # Take key sentences from beginning, middle, and end
        summary_sentences = []
        total = len(valid_sentences)
        
        if total > 0:
            # First sentence
            summary_sentences.append(valid_sentences[0])
            
            if total > 2 and max_sentences > 1:
                # Middle sentence
                summary_sentences.append(valid_sentences[total // 2])
            
            if total > 3 and max_sentences > 2:
                # Another from middle section
                summary_sentences.append(valid_sentences[total // 3])
            
            if total > 4 and max_sentences > 3:
                # Late-middle sentence
                summary_sentences.append(valid_sentences[2 * total // 3])
            
            if total > 1 and max_sentences > 4:
                # Last sentence
                summary_sentences.append(valid_sentences[-1])
        
        # Limit to max_sentences
        summary = ' '.join(summary_sentences[:max_sentences])
        
        # Clean up the summary
        summary = re.sub(r'\s+', ' ', summary)
        summary = re.sub(r'\([^)]{100,}\)', '', summary)  # Remove very long parentheticals
        
        return summary.strip()
    
    def process_all_chapters(self) -> List[Dict]:
        """Process all chapters and generate dataset"""
        # Parse content table
        self.chapters = self.parse_content_table()
        
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters...")
        
        for idx, chapter in enumerate(self.chapters, 1):
            chapter_num = chapter['chapter_number']
            chapter_name = chapter['chapter_name']
            start_page = chapter['start_page']
            end_page = chapter['end_page']
            
            print(f"\n[{idx}/{len(self.chapters)}] Chapter {chapter_num}: {chapter_name}")
            print(f"   Pages {start_page}-{end_page}")
            
            # Extract chapter text
            raw_text = self.extract_chapter_text(start_page, end_page)
            
            if not raw_text or len(raw_text) < 100:
                print(f"   ⚠️  Warning: Minimal content found")
                # Create 3 placeholder entries
                for i in range(3):
                    dataset.append({
                        'book_title': self.book_title,
                        'chapter_number': chapter_num,
                        'chapter_name': chapter_name,
                        'topic_name': chapter_name,
                        'content': '',
                        'summary': 'Content not available.'
                    })
                continue
            
            # Clean the text
            cleaned_text = self.clean_text(raw_text)
            
            # Split into 3 chunks
            chunks = self.split_into_chunks(cleaned_text, num_chunks=3)
            
            # Process each chunk
            for chunk_idx, chunk in enumerate(chunks, 1):
                if not chunk:
                    chunk = ""
                    
                topic_name = self.extract_topic_name(chunk, chapter_name)
                summary = self.generate_summary(chunk)
                
                dataset.append({
                    'book_title': self.book_title,
                    'chapter_number': chapter_num,
                    'chapter_name': chapter_name,
                    'topic_name': topic_name,
                    'content': chunk,
                    'summary': summary
                })
                
                print(f"   ✓ Chunk {chunk_idx}/3: {len(chunk)} chars, topic: {topic_name[:50]}")
        
        print(f"\n✅ Processing complete: {len(dataset)} total rows")
        return dataset
    
    def save_to_csv(self, dataset: List[Dict], output_path: str):
        """Save dataset to CSV file"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'book_title', 'chapter_number', 'chapter_name', 
                'topic_name', 'content', 'summary'
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
    print("Nelson Pediatrics Dataset Creation Tool")
    print("=" * 70)
    
    # Initialize processor
    processor = NelsonPediatricsProcessor(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt'
    )
    
    # Process all chapters
    dataset = processor.process_all_chapters()
    
    # Save outputs
    processor.save_to_csv(dataset, 'nelson_pediatrics_dataset.csv')
    processor.save_to_json(dataset, 'nelson_pediatrics_dataset.json')
    
    # Print statistics
    print("\n" + "=" * 70)
    print("📈 DATASET STATISTICS")
    print("=" * 70)
    print(f"Total rows: {len(dataset)}")
    print(f"Total chapters: {len(dataset) // 3}")
    print(f"Chunks per chapter: 3")
    print(f"Columns: book_title, chapter_number, chapter_name, topic_name, content, summary")
    print("\n✅ Dataset creation complete!")


if __name__ == '__main__':
    main()
