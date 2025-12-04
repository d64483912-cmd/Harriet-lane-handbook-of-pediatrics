#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset - V4 FINAL
Fixed chunking: 15 chunks per chapter, 250-400 tokens each
"""

import re
import csv
import json
from typing import List, Dict

class NelsonPediatricsV4:
    def __init__(self, content_table_path: str, text_path: str):
        self.content_table_path = content_table_path
        self.text_path = text_path
        self.book_title = "Nelson Textbook of Pediatrics"
        self.chapters = []
        
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
        for chapter_range, category in self.category_taxonomy.items():
            if chapter_num in chapter_range:
                return category
        return "General Pediatrics"
    
    def parse_content_table(self) -> List[Dict]:
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
            
        return chapters
    
    def extract_chapter_text(self, start_page: int, end_page: int) -> str:
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
    
    def clean_text(self, text: str) -> str:
        # Remove system markers
        text = re.sub(r'Downloaded for .+ at .+ from ClinicalKey\.com.*?reserved\.', '', text, flags=re.DOTALL)
        text = re.sub(r'>> CHAPTER:.*?\n', '', text)
        text = re.sub(r'Chapter \d+\s+[uv]\s+.*?\n', '', text)
        
        # Fix hyphenation
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def chunk_by_token_target(self, text: str, num_chunks: int = 15) -> List[str]:
        """
        Split text into exactly num_chunks chunks, each ~250-400 tokens
        """
        if not text or len(text) < 100:
            return []
        
        words = text.split()
        total_words = len(words)
        
        # If text is very short, return as single chunk
        if total_words < 150:
            return [text]
        
        # Calculate words per chunk
        words_per_chunk = total_words // num_chunks
        
        # Ensure each chunk is 250-400 words (tokens)
        if words_per_chunk < 200:
            # Text too short for 15 chunks, reduce chunk count
            num_chunks = max(1, total_words // 300)
            words_per_chunk = total_words // num_chunks
        
        chunks = []
        current_pos = 0
        
        for i in range(num_chunks):
            # Calculate chunk size
            if i == num_chunks - 1:
                # Last chunk gets remaining words
                chunk_words = words[current_pos:]
            else:
                target_end = current_pos + words_per_chunk
                
                # Find sentence boundary near target
                chunk_end = target_end
                search_start = max(current_pos, target_end - 50)
                search_end = min(len(words), target_end + 50)
                
                # Look for sentence endings
                for j in range(target_end, search_end):
                    if j < len(words) and words[j].endswith(('.', '!', '?')):
                        chunk_end = j + 1
                        break
                
                chunk_words = words[current_pos:chunk_end]
                current_pos = chunk_end
            
            if chunk_words:
                chunk_text = ' '.join(chunk_words)
                chunks.append(chunk_text)
        
        return chunks
    
    def extract_topic_name(self, chapter_name: str, chunk_index: int, total_chunks: int) -> str:
        """Extract concise topic name from chapter name"""
        name = re.sub(r'\s+', ' ', chapter_name).strip()
        words = name.split()
        
        # For single chunk, use first 3-4 words
        if total_chunks == 1:
            return ' '.join(words[:min(4, len(words))])
        
        # For multiple chunks, create variations
        if len(words) <= 3:
            return f"{name} Part {chunk_index + 1}"
        
        # Use different parts of chapter name for different chunks
        if chunk_index == 0:
            # First chunk: beginning of chapter name
            return ' '.join(words[:min(3, len(words))])
        elif chunk_index == total_chunks - 1:
            # Last chunk: end of chapter name
            return ' '.join(words[-min(3, len(words)):])
        else:
            # Middle chunks: rotate through chapter name
            start_idx = (chunk_index % max(1, len(words) - 2))
            return ' '.join(words[start_idx:start_idx + 3])
    
    def generate_summary(self, text: str) -> str:
        """Generate 3-5 sentence summary"""
        if not text or len(text) < 50:
            return ""
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter good sentences
        good_sentences = []
        for s in sentences:
            s = s.strip()
            # Skip tables, figures, very short/long sentences
            if 40 < len(s) < 400 and not re.match(r'^(Table|Fig|Chapter|Downloaded)', s):
                good_sentences.append(s)
        
        if not good_sentences:
            return text[:300] + "..."
        
        # Select 3-5 sentences strategically
        selected = []
        if len(good_sentences) >= 1:
            selected.append(good_sentences[0])
        if len(good_sentences) >= 3:
            selected.append(good_sentences[len(good_sentences) // 2])
        if len(good_sentences) >= 2:
            selected.append(good_sentences[-1])
        
        # Add more if needed
        for s in good_sentences:
            if s not in selected and len(selected) < 5:
                selected.append(s)
        
        summary = ' '.join(selected[:5])
        return summary if len(summary) >= 50 else text[:300] + "..."
    
    def process_all_chapters(self) -> List[Dict]:
        self.chapters = self.parse_content_table()
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters (15 chunks each)...\n")
        
        for idx, chapter in enumerate(self.chapters, 1):
            chapter_num = chapter['chapter_number']
            chapter_name = chapter['chapter_name']
            start_page = chapter['start_page']
            end_page = chapter['end_page']
            category = self.get_category(chapter_num)
            
            if idx % 50 == 0:
                print(f"[{idx}/{len(self.chapters)}] Processed {len(dataset)} chunks total")
            
            # Extract and clean text
            raw_text = self.extract_chapter_text(start_page, end_page)
            if not raw_text or len(raw_text) < 200:
                continue
            
            cleaned_text = self.clean_text(raw_text)
            if not cleaned_text or len(cleaned_text) < 200:
                continue
            
            # Create 15 chunks
            chunks = self.chunk_by_token_target(cleaned_text, num_chunks=15)
            
            for chunk_idx, chunk in enumerate(chunks):
                if not chunk or len(chunk.split()) < 50:
                    continue
                
                topic_name = self.extract_topic_name(chapter_name, chunk_idx, len(chunks))
                summary = self.generate_summary(chunk)
                
                if not summary or len(summary) < 50:
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
        
        print(f"\n✅ Complete: {len(dataset)} records generated")
        print(f"   Target: ~{len(self.chapters) * 15:,}")
        print(f"   Achievement: {len(dataset)/(len(self.chapters)*15)*100:.1f}%")
        
        return dataset
    
    def save_to_csv(self, dataset: List[Dict], output_path: str):
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'book_title', 'chapter_number', 'chapter_name',
                'topic_name', 'content', 'category', 'summary'
            ])
            writer.writeheader()
            writer.writerows(dataset)
        print(f"💾 CSV: {output_path}")
    
    def save_to_json(self, dataset: List[Dict], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON: {output_path}")


def main():
    print("=" * 80)
    print("Nelson Pediatrics V4 FINAL - Fixed Chunking Algorithm")
    print("=" * 80)
    
    processor = NelsonPediatricsV4(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt'
    )
    
    dataset = processor.process_all_chapters()
    
    processor.save_to_csv(dataset, 'dataset/nelson_pediatrics_dataset_v4_final.csv')
    processor.save_to_json(dataset, 'dataset/nelson_pediatrics_dataset_v4_final.json')
    
    # Quick validation
    if dataset:
        sample_tokens = [len(r['content'].split()) for r in dataset[:100]]
        avg_tokens = sum(sample_tokens) / len(sample_tokens)
        print(f"\n📊 Quick Stats:")
        print(f"   Avg tokens (first 100): {avg_tokens:.0f}")
        print(f"   Min: {min(sample_tokens)} | Max: {max(sample_tokens)}")
    
    print(f"\n✅ V4 FINAL dataset generation complete!")


if __name__ == '__main__':
    main()
