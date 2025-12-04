#!/usr/bin/env python3
"""
Nelson Pediatrics Dataset - V3 with Mistral AI Summarization
Production quality with AI-powered clinical summaries
"""

import re
import csv
import json
import os
import time
from typing import List, Dict
from pathlib import Path

# Mistral AI integration
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    print("⚠️  Mistral AI not available, using rule-based summarization")


class NelsonPediatricsV3Mistral:
    def __init__(self, content_table_path: str, text_path: str, api_key: str = None):
        self.content_table_path = content_table_path
        self.text_path = text_path
        self.book_title = "Nelson Textbook of Pediatrics"
        self.chapters = []
        
        # Initialize Mistral client
        self.api_key = api_key or os.getenv('MISTRAL_API_KEY')
        if MISTRAL_AVAILABLE and self.api_key:
            self.mistral_client = Mistral(api_key=self.api_key)
            print("✓ Mistral AI enabled for summarization")
        else:
            self.mistral_client = None
            print("⚠️  Using rule-based summarization")
        
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
        
        self.api_call_count = 0
        self.api_call_limit = 100  # Rate limit safety
    
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
        """Advanced text cleaning"""
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
    
    def semantic_chunking(self, text: str, target_tokens: int = 300, max_chunks: int = 3) -> List[str]:
        """Semantic chunking with 250-400 token targets"""
        if not text or len(text) < 100:
            return []
        
        words = text.split()
        total_tokens = len(words)
        
        if total_tokens < 150:
            return [text]
        
        tokens_per_chunk = max(target_tokens, total_tokens // max_chunks)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = len(para.split())
            
            if current_tokens > 0 and current_tokens + para_tokens > tokens_per_chunk * 1.3:
                chunks.append(' '.join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
            
            if len(chunks) >= max_chunks - 1:
                break
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        if len(chunks) > 0 and len(chunks) < len(paragraphs):
            remaining_idx = sum(len(c.split('\n\n')) for c in chunks)
            if remaining_idx < len(paragraphs):
                remaining = ' '.join(paragraphs[remaining_idx:])
                if remaining:
                    chunks[-1] += ' ' + remaining
        
        return chunks[:max_chunks]
    
    def extract_short_topic(self, chunk_text: str, chapter_name: str) -> str:
        """Extract short topic (2-4 words)"""
        if not chunk_text:
            return ' '.join(chapter_name.split()[:3])
        
        lines = chunk_text.split('\n')
        
        for line in lines[:10]:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            if 10 < len(line) < 50 and line.isupper():
                return ' '.join(line.split()[:3]).title()
            
            if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){1,3}$', line):
                return ' '.join(line.split()[:3])
        
        sentences = re.split(r'[.!?]\s+', chunk_text)
        for sent in sentences[:2]:
            sent = sent.strip()
            if 20 < len(sent) < 150:
                words = sent.split()
                topic_words = []
                for w in words[:6]:
                    w = re.sub(r'[^\w\s]', '', w)
                    if w and (w[0].isupper() or len(topic_words) < 3):
                        topic_words.append(w)
                    if len(topic_words) >= 3:
                        break
                
                if topic_words:
                    return ' '.join(topic_words[:3])
        
        return ' '.join(chapter_name.split()[:3])
    
    def generate_summary_mistral(self, chunk_text: str, topic: str, category: str) -> str:
        """Generate summary using Mistral AI"""
        if not self.mistral_client or self.api_call_count >= self.api_call_limit:
            return self.generate_summary_rule_based(chunk_text)
        
        try:
            # Limit text length for API
            text_sample = chunk_text[:1500] if len(chunk_text) > 1500 else chunk_text
            
            prompt = f"""You are a medical expert. Summarize this pediatric medical text in exactly 3-5 clear, clinical sentences.

Topic: {topic}
Category: {category}

Text:
{text_sample}

Requirements:
- Write 3-5 complete sentences
- Focus on clinical facts: diagnosis, treatment, symptoms, management
- Use medical terminology appropriately
- Be concise and factual
- No citations or references

Summary:"""
            
            response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            self.api_call_count += 1
            
            summary = response.choices[0].message.content.strip()
            
            # Validate summary
            sentences = re.split(r'[.!?]\s+', summary)
            if 3 <= len(sentences) <= 6 and len(summary) > 100:
                return summary
            else:
                return self.generate_summary_rule_based(chunk_text)
            
        except Exception as e:
            print(f"   API error: {e}, falling back to rule-based")
            return self.generate_summary_rule_based(chunk_text)
    
    def generate_summary_rule_based(self, chunk_text: str) -> str:
        """Fallback rule-based summary"""
        if not chunk_text or len(chunk_text) < 100:
            return ""
        
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        
        clinical_sentences = []
        for s in sentences:
            s = s.strip()
            if 40 < len(s) < 350:
                if not re.match(r'^(Table|Fig|Chapter|Downloaded|\d+\.|>>)', s):
                    if any(term in s.lower() for term in ['patient', 'treatment', 'diagnosis', 'child', 'clinical', 'symptom', 'therapy', 'disease', 'condition']):
                        clinical_sentences.append(s)
                    elif len(clinical_sentences) < 3:
                        clinical_sentences.append(s)
        
        if not clinical_sentences:
            clinical_sentences = [s.strip() for s in sentences[:5] if 30 < len(s.strip()) < 400]
        
        if len(clinical_sentences) == 0:
            return chunk_text[:300].strip() + "..."
        
        summary_sentences = []
        total = len(clinical_sentences)
        
        summary_sentences.append(clinical_sentences[0])
        
        if total >= 3:
            summary_sentences.append(clinical_sentences[total // 2])
        
        if total >= 5:
            summary_sentences.append(clinical_sentences[2 * total // 3])
        
        if total >= 2 and clinical_sentences[-1] not in summary_sentences:
            summary_sentences.append(clinical_sentences[-1])
        
        summary = ' '.join(summary_sentences[:5])
        summary = re.sub(r'\s+', ' ', summary)
        
        return summary.strip()
    
    def process_all_chapters(self) -> List[Dict]:
        """Process all chapters"""
        self.chapters = self.parse_content_table()
        dataset = []
        
        print(f"\n📊 Processing {len(self.chapters)} chapters with AI summarization...\n")
        
        for idx, chapter in enumerate(self.chapters, 1):
            chapter_num = chapter['chapter_number']
            chapter_name = chapter['chapter_name']
            start_page = chapter['start_page']
            end_page = chapter['end_page']
            category = self.get_category(chapter_num)
            
            if idx % 25 == 0:
                print(f"[{idx}/{len(self.chapters)}] Processed {len(dataset)} chunks, API calls: {self.api_call_count}")
            
            raw_text = self.extract_chapter_text(start_page, end_page)
            
            if not raw_text or len(raw_text) < 200:
                continue
            
            cleaned_text = self.advanced_text_cleaning(raw_text)
            chunks = self.semantic_chunking(cleaned_text, target_tokens=300, max_chunks=3)
            
            for chunk in chunks:
                if not chunk or len(chunk) < 100:
                    continue
                
                topic_name = self.extract_short_topic(chunk, chapter_name)
                
                # Use Mistral AI for summary
                if self.mistral_client:
                    summary = self.generate_summary_mistral(chunk, topic_name, category)
                    time.sleep(0.5)  # Rate limiting
                else:
                    summary = self.generate_summary_rule_based(chunk)
                
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
        
        print(f"\n✅ Complete: {len(dataset)} records, {self.api_call_count} AI summaries generated")
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
    print("Nelson Pediatrics V3 - AI-Powered Summarization")
    print("=" * 70)
    
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print("❌ MISTRAL_API_KEY not set, using rule-based summarization only")
    
    processor = NelsonPediatricsV3Mistral(
        content_table_path='nelson_pediatrics_content_table.txt',
        text_path='nelson_pediatrics.txt',
        api_key=api_key
    )
    
    dataset = processor.process_all_chapters()
    
    processor.save_to_csv(dataset, 'nelson_pediatrics_dataset_v3_final.csv')
    processor.save_to_json(dataset, 'nelson_pediatrics_dataset_v3_final.json')
    
    print(f"\n✅ Dataset generation complete!")
    print(f"   Records: {len(dataset)}")
    print(f"   AI summaries: {processor.api_call_count}")


if __name__ == '__main__':
    main()
