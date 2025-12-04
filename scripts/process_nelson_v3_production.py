#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset - V3 PRODUCTION
15 chunks per chapter with topics from table of contents
"""

import re
import csv
import json
from typing import List, Dict

class NelsonPediatricsV3Production:
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
        """Parse table of contents to get chapter names as topic references"""
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
            
        print(f"✓ Parsed {len(chapters)} chapters from table of contents")
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
            
            if buffer and line and line[0].islower():
                buffer += " " + line
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
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def smart_chunking_15(self, text: str, max_chunks: int = 15) -> List[str]:
        """Smart chunking: 15 chunks per chapter, 250-400 tokens each"""
        if not text or len(text) < 100:
            return []
        
        words = text.split()
        total_tokens = len(words)
        
        # If chapter is very short, return as-is
        if total_tokens < 200:
            return [text]
        
        # Calculate optimal tokens per chunk
        target_tokens = max(250, min(400, total_tokens // max_chunks))
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk_words = []
        current_tokens = 0
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            sent_tokens = len(sent.split())
            
            # If adding this sentence would exceed target
            if current_tokens > 0 and current_tokens + sent_tokens > target_tokens:
                # Save current chunk if we haven't reached max chunks
                if len(chunks) < max_chunks - 1:
                    chunks.append(' '.join(current_chunk_words))
                    current_chunk_words = [sent]
                    current_tokens = sent_tokens
                else:
                    # Last chunk - add everything remaining
                    current_chunk_words.append(sent)
                    current_tokens += sent_tokens
            else:
                current_chunk_words.append(sent)
                current_tokens += sent_tokens
        
        # Add final chunk
        if current_chunk_words:
            chunks.append(' '.join(current_chunk_words))
        
        # If we have fewer chunks than max_chunks, split large chunks
        while len(chunks) < max_chunks and any(len(c.split()) > 500 for c in chunks):
            new_chunks = []
            for chunk in chunks:
                chunk_tokens = len(chunk.split())
                if chunk_tokens > 500 and len(chunks) + len(new_chunks) < max_chunks:
                    # Split this chunk in half
                    mid_point = len(chunk) // 2
                    split_at = chunk.rfind('. ', 0, mid_point) + 1
                    if split_at > 0:
                        new_chunks.append(chunk[:split_at].strip())
                        new_chunks.append(chunk[split_at:].strip())
                    else:
                        new_chunks.append(chunk)
                else:
                    new_chunks.append(chunk)
            chunks = new_chunks
            if len(chunks) >= max_chunks:
                break
        
        return chunks[:max_chunks]
    
    def extract_topic_from_chapter_name(self, chapter_name: str, chunk_index: int, total_chunks: int) -> str:
        """Extract topic from chapter name with variation for multiple chunks"""
        # Clean the chapter name
        name = re.sub(r'\s+', ' ', chapter_name).strip()
        
        # Extract key clinical terms (2-5 words)
        words = name.split()
        
        # For multiple chunks, create variations
        if total_chunks == 1:
            return ' '.join(words[:min(4, len(words))])
        
        # For multiple chunks, use different parts of the chapter name
        if len(words) <= 3:
            # Short name, use as-is with part number
            return f"{name} Part {chunk_index + 1}"
        elif len(words) <= 6:
            # Medium name, split into parts
            if chunk_index == 0:
                return ' '.join(words[:3])
            elif chunk_index == total_chunks - 1:
                return ' '.join(words[-3:])
            else:
                return ' '.join(words[:4])
        else:
            # Long name, extract different segments
            segment_size = max(3, len(words) // 3)
            start_idx = min(chunk_index * 2, len(words) - 3)
            return ' '.join(words[start_idx:start_idx + 3])
    
    def extract_topic_from_content(self, chunk_text: str, chapter_name: str, chunk_idx: int) -> str:
        """Extract specific clinical topic from chunk content"""
        lines = chunk_text.split('\n')
        
        # Look for section headings
        for line in lines[:20]:
            line = line.strip()
            if not line:
                continue
            
            # ALL CAPS heading (15-60 chars)
            if 15 <= len(line) <= 60 and line.isupper():
                if not re.search(r'\d{3,}', line) and not line.startswith('TABLE'):
                    words = line.split()
                    topic = ' '.join(words[:min(4, len(words))]).title()
                    if len(topic) >= 10:
                        return topic
            
            # Title Case heading
            if 15 <= len(line) <= 60 and re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$', line):
                words = line.split()
                if 2 <= len(words) <= 5:
                    return ' '.join(words[:4])
        
        # Extract from first meaningful sentence
        sentences = re.split(r'[.!?]\s+', chunk_text)
        for sent in sentences[:3]:
            sent = sent.strip()
            if 40 < len(sent) < 200:
                # Extract noun phrase
                words = sent.split()
                topic_words = []
                for w in words[:10]:
                    clean_w = re.sub(r'[^\w\s-]', '', w)
                    if clean_w and (clean_w[0].isupper() or len(topic_words) == 0):
                        topic_words.append(clean_w)
                        if len(topic_words) >= 3:
                            break
                
                if 2 <= len(topic_words) <= 4:
                    return ' '.join(topic_words)
        
        # Fallback: use chapter name with chunk number
        return self.extract_topic_from_chapter_name(chapter_name, chunk_idx, 1)
    
    def generate_clinical_summary(self, chunk_text: str) -> str:
        """Generate 3-5 sentence clinical summary"""
        if not chunk_text or len(chunk_text) < 100:
            return ""
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        
        # Clinical keywords
        clinical_keywords = [
            'patient', 'treatment', 'diagnosis', 'therapy', 'clinical', 'symptom',
            'disease', 'condition', 'children', 'child', 'pediatric', 'infant',
            'management', 'care', 'risk', 'health', 'syndrome', 'disorder',
            'complication', 'prevention', 'screening', 'assessment'
        ]
        
        # Filter clinical sentences
        clinical_sentences = []
        for s in sentences:
            s = s.strip()
            if 40 < len(s) < 450:
                # Skip tables, figures, references
                if re.match(r'^(Table|Fig|Chapter|Downloaded|See Chapter|\d+\.|Reference)', s):
                    continue
                
                s_lower = s.lower()
                has_clinical = any(keyword in s_lower for keyword in clinical_keywords)
                
                if has_clinical:
                    clinical_sentences.append(s)
        
        # If no clinical sentences, use any good sentences
        if not clinical_sentences:
            clinical_sentences = [s.strip() for s in sentences if 40 < len(s.strip()) < 450][:8]
        
        # Select 3-5 strategically
        selected = []
        
        if len(clinical_sentences) >= 1:
            selected.append(clinical_sentences[0])
        
        if len(clinical_sentences) >= 3:
            mid_idx = len(clinical_sentences) // 2
            if clinical_sentences[mid_idx] not in selected:
                selected.append(clinical_sentences[mid_idx])
        
        if len(clinical_sentences) >= 5:
            later_idx = 2 * len(clinical_sentences) // 3
            if clinical_sentences[later_idx] not in selected:
                selected.append(clinical_sentences[later_idx])
        
        if len(clinical_sentences) >= 2:
            if clinical_sentences[-1] not in selected:
                selected.append(clinical_sentences[-1])
        
        # Fill to 3-5 sentences
        for sent in clinical_sentences:
            if sent not in selected and len(selected) < 5:
                selected.append(sent)
        
        summary = ' '.join(selected[:5])
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        return summary if len(summary) >= 50 else chunk_text[:300] + "..."
    
    def process_all_chapters(self) -> List[Dict]:
        """Process all chapters with 15 chunks each"""
        self.chapters = self.parse_content_table()
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters (15 chunks each)...\n")
        
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
            
            # Create 15 chunks per chapter
            chunks = self.smart_chunking_15(cleaned_text, max_chunks=15)
            
            for chunk_idx, chunk in enumerate(chunks):
                if not chunk or len(chunk) < 100:
                    continue
                
                # Extract topic from content AND chapter name
                topic_name = self.extract_topic_from_content(chunk, chapter_name, chunk_idx)
                
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
        
        print(f"\n✅ Complete: {len(dataset)} high-quality records (target: ~{len(self.chapters) * 15})")
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
    print("Nelson Pediatrics V3 PRODUCTION - 15 Chunks Per Chapter")
    print("=" * 80)
    
    processor = NelsonPediatricsV3Production(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt'
    )
    
    dataset = processor.process_all_chapters()
    
    processor.save_to_csv(dataset, 'dataset/nelson_pediatrics_dataset_v3_final.csv')
    processor.save_to_json(dataset, 'dataset/nelson_pediatrics_dataset_v3_final.json')
    
    print(f"\n✅ V3 PRODUCTION dataset complete!")
    print(f"   Total records: {len(dataset)}")
    print(f"   Average per chapter: {len(dataset) / 697:.1f}")
    print(f"   Ready for production use!")


if __name__ == '__main__':
    main()
