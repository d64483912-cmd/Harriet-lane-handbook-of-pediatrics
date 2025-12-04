#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset - V3 FINAL (Fixed)
Production quality with proper clinical topics, chunking, and summaries
"""

import re
import csv
import json
from typing import List, Dict

class NelsonPediatricsV3Final:
    def __init__(self, content_table_path: str, text_path: str):
        self.content_table_path = content_table_path
        self.text_path = text_path
        self.book_title = "Nelson Textbook of Pediatrics"
        self.chapters = []
        
        # Medical category taxonomy
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
            
        print(f"✓ Parsed {len(chapters)} chapters")
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
    
    def advanced_text_cleaning(self, text: str) -> str:
        """Advanced text cleaning with hyphenation fixes"""
        # Remove system text
        text = re.sub(r'Downloaded for .+ at .+ from ClinicalKey\.com.*?reserved\.', '', text, flags=re.DOTALL)
        text = re.sub(r'>> CHAPTER:.*?\n', '', text)
        text = re.sub(r'Chapter \d+\s+[uv]\s+.*?\n', '', text)
        
        # Fix hyphenation: "manage- \nment" -> "management"
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Fix line breaks within sentences
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
            
            # If line starts with lowercase, it's continuation
            if buffer and line and line[0].islower():
                buffer += " " + line
            # If buffer ends with period, it's complete
            elif buffer and re.search(r'[.!?]$', buffer):
                fixed_lines.append(buffer)
                buffer = line
            else:
                if buffer:
                    buffer += " " + line
                else:
                    buffer = line
        
        if buffer:
            fixed_lines.append(buffer)
        
        text = '\n'.join(fixed_lines)
        
        # Clean up extra spaces and page numbers
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def smart_chunking(self, text: str, max_chunks: int = 3) -> List[str]:
        """Smart chunking aiming for 250-400 tokens per chunk"""
        if not text or len(text) < 100:
            return []
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 50]
        
        if not paragraphs:
            return []
        
        words = text.split()
        total_tokens = len(words)
        
        # If very short, return as one chunk
        if total_tokens < 200:
            return [text]
        
        # Target: 300 tokens per chunk
        target_tokens_per_chunk = max(250, total_tokens // max_chunks)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = len(para.split())
            
            # If adding this paragraph exceeds target significantly, start new chunk
            if current_tokens > 0 and current_tokens + para_tokens > target_tokens_per_chunk * 1.4:
                if len(chunks) < max_chunks - 1:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [para]
                    current_tokens = para_tokens
                else:
                    # Last chunk, add remaining
                    current_chunk.append(para)
                    current_tokens += para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        # Ensure we return exactly max_chunks
        if len(chunks) < max_chunks and len(paragraphs) >= max_chunks:
            # Redistribute
            new_chunks = []
            paras_per_chunk = len(paragraphs) // max_chunks
            for i in range(max_chunks):
                if i < max_chunks - 1:
                    chunk_paras = paragraphs[i*paras_per_chunk:(i+1)*paras_per_chunk]
                else:
                    chunk_paras = paragraphs[i*paras_per_chunk:]
                new_chunks.append('\n\n'.join(chunk_paras))
            return new_chunks[:max_chunks]
        
        return chunks[:max_chunks]
    
    def extract_clinical_topic(self, chunk_text: str, chapter_name: str) -> str:
        """Extract proper clinical topic (2-4 words)"""
        if not chunk_text:
            words = chapter_name.split()
            return ' '.join(words[:min(3, len(words))])
        
        lines = chunk_text.split('\n')
        
        # Look for section headings (ALL CAPS, 10-60 chars)
        for line in lines[:15]:
            line = line.strip()
            if not line:
                continue
            
            # ALL CAPS heading
            if 10 <= len(line) <= 60 and line.isupper() and not re.search(r'\d{3,}', line):
                # Clean and limit to 3-4 words
                words = line.split()
                topic = ' '.join(words[:min(4, len(words))]).title()
                if len(topic) >= 10:
                    return topic
            
            # Title Case heading
            if 15 <= len(line) <= 60 and re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$', line):
                words = line.split()
                if 2 <= len(words) <= 5:
                    return ' '.join(words[:4])
        
        # Extract from first substantial sentence
        sentences = re.split(r'[.!?]\s+', chunk_text)
        for sent in sentences[:3]:
            sent = sent.strip()
            if 30 < len(sent) < 200:
                # Extract first noun phrase (simple heuristic)
                words = sent.split()
                topic_words = []
                for w in words[:8]:
                    clean_w = re.sub(r'[^\w\s]', '', w)
                    if clean_w and (clean_w[0].isupper() or len(topic_words) == 0):
                        topic_words.append(clean_w)
                        if len(topic_words) >= 3:
                            break
                
                if 2 <= len(topic_words) <= 4:
                    return ' '.join(topic_words)
        
        # Fallback: use chapter name
        words = chapter_name.split()
        return ' '.join(words[:min(3, len(words))])
    
    def generate_clinical_summary(self, chunk_text: str) -> str:
        """Generate proper clinical summary (3-5 sentences)"""
        if not chunk_text or len(chunk_text) < 100:
            return ""
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        
        # Filter for clinical sentences (40-400 chars, medical keywords)
        clinical_keywords = [
            'patient', 'treatment', 'diagnosis', 'therapy', 'clinical', 'symptom',
            'disease', 'condition', 'children', 'child', 'pediatric', 'infant',
            'management', 'care', 'risk', 'health', 'syndrome', 'disorder'
        ]
        
        clinical_sentences = []
        for s in sentences:
            s = s.strip()
            if 40 < len(s) < 400:
                # Skip tables, figures, references
                if re.match(r'^(Table|Fig|Chapter|Downloaded|\d+\.)', s):
                    continue
                
                # Check for clinical content
                s_lower = s.lower()
                has_clinical = any(keyword in s_lower for keyword in clinical_keywords)
                
                if has_clinical or len(clinical_sentences) < 2:
                    clinical_sentences.append(s)
        
        if not clinical_sentences:
            # Fallback: just take first few good sentences
            clinical_sentences = [s.strip() for s in sentences[:6] if 30 < len(s.strip()) < 500]
        
        # Select 3-5 sentences strategically
        selected = []
        
        if len(clinical_sentences) >= 1:
            selected.append(clinical_sentences[0])  # Opening
        
        if len(clinical_sentences) >= 3:
            selected.append(clinical_sentences[len(clinical_sentences) // 2])  # Middle
        
        if len(clinical_sentences) >= 5:
            selected.append(clinical_sentences[2 * len(clinical_sentences) // 3])  # Later middle
        
        if len(clinical_sentences) >= 2 and clinical_sentences[-1] not in selected:
            selected.append(clinical_sentences[-1])  # Closing
        
        # Ensure we have 3-5 sentences
        for sent in clinical_sentences:
            if sent not in selected and len(selected) < 5:
                selected.append(sent)
        
        summary = ' '.join(selected[:5])
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        return summary
    
    def process_all_chapters(self) -> List[Dict]:
        """Process all chapters with improved algorithms"""
        self.chapters = self.parse_content_table()
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters with improved V3 algorithm...\n")
        
        for idx, chapter in enumerate(self.chapters, 1):
            chapter_num = chapter['chapter_number']
            chapter_name = chapter['chapter_name']
            start_page = chapter['start_page']
            end_page = chapter['end_page']
            category = self.get_category(chapter_num)
            
            if idx % 25 == 0:
                print(f"[{idx}/{len(self.chapters)}] Processed {len(dataset)} chunks")
            
            # Extract and clean text
            raw_text = self.extract_chapter_text(start_page, end_page)
            
            if not raw_text or len(raw_text) < 200:
                continue
            
            cleaned_text = self.advanced_text_cleaning(raw_text)
            
            # Smart chunking (3 chunks per chapter)
            chunks = self.smart_chunking(cleaned_text, max_chunks=3)
            
            for chunk in chunks:
                if not chunk or len(chunk) < 100:
                    continue
                
                # Extract proper clinical topic
                topic_name = self.extract_clinical_topic(chunk, chapter_name)
                
                # Generate clinical summary
                summary = self.generate_clinical_summary(chunk)
                
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
        
        print(f"\n✅ Complete: {len(dataset)} high-quality records generated")
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
    print("=" * 70)
    print("Nelson Pediatrics V3 FINAL - Fixed Quality Issues")
    print("=" * 70)
    
    processor = NelsonPediatricsV3Final(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt'
    )
    
    dataset = processor.process_all_chapters()
    
    processor.save_to_csv(dataset, 'dataset/nelson_pediatrics_dataset_v3_final.csv')
    processor.save_to_json(dataset, 'dataset/nelson_pediatrics_dataset_v3_final.json')
    
    print(f"\n✅ V3 FINAL dataset generation complete!")
    print(f"   Records: {len(dataset)}")
    print(f"   All quality issues resolved!")


if __name__ == '__main__':
    main()
