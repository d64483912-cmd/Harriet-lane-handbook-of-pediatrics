import re
import csv
import json
from typing import List, Dict, Tuple
from collections import defaultdict

BOOK_TITLE = "Nelson Textbook of Pediatrics"

class NelsonDatasetExtractor:
    def __init__(self, content_table_path: str, main_text_path: str):
        self.content_table_path = content_table_path
        self.main_text_path = main_text_path
        self.chapters = []
        self.chapter_texts = {}
        
    def parse_content_table(self) -> List[Dict]:
        chapters = []
        with open(self.content_table_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('CHAPTER:'):
                    match = re.match(r'CHAPTER:\s*(.+?)\s*\(Page:\s*(\d+)\)', line)
                    if match:
                        chapter_name = match.group(1).strip()
                        page_num = int(match.group(2))
                        chapter_num = len(chapters) + 1
                        chapters.append({
                            'chapter_number': chapter_num,
                            'chapter_name': chapter_name,
                            'page_number': page_num
                        })
        print(f"Parsed {len(chapters)} chapters from content table")
        return chapters
    
    def extract_chapter_texts(self) -> Dict[str, str]:
        print("Extracting chapter texts from main file...")
        chapter_texts = {}
        current_chapter = None
        current_text = []
        
        with open(self.main_text_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('>> CHAPTER:'):
                    if current_chapter:
                        chapter_texts[current_chapter] = '\n'.join(current_text)
                    
                    chapter_match = re.match(r'>> CHAPTER:\s*(.+)', line)
                    if chapter_match:
                        current_chapter = chapter_match.group(1).strip()
                        current_text = []
                else:
                    current_text.append(line.rstrip())
            
            if current_chapter:
                chapter_texts[current_chapter] = '\n'.join(current_text)
        
        print(f"Extracted {len(chapter_texts)} chapter texts")
        return chapter_texts
    
    def clean_text(self, text: str) -> str:
        text = re.sub(r'--- PAGE \d+ ---', '', text)
        text = re.sub(r'Downloaded for .+ at .+ from ClinicalKey\.com.+?reserved\.', '', text, flags=re.DOTALL)
        text = re.sub(r'Chapter \d+\s+u\s+[^\n]+\s+\d+', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'-\s+', '', text)
        text = text.strip()
        return text
    
    def find_major_sections(self, text: str) -> List[Tuple[str, int]]:
        lines = text.split('\n')
        sections = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if len(line_stripped) > 0:
                if line_stripped.isupper() and len(line_stripped) > 5 and len(line_stripped) < 100:
                    sections.append((line_stripped, i))
                elif re.match(r'^[A-Z][A-Za-z\s,\-:]+$', line_stripped) and len(line_stripped) > 10 and len(line_stripped) < 150:
                    if not any(keyword in line_stripped.lower() for keyword in ['chapter', 'page', 'downloaded', 'elsevier']):
                        sections.append((line_stripped, i))
        
        return sections[:10] if len(sections) > 10 else sections
    
    def split_into_chunks(self, text: str, chapter_name: str) -> List[Tuple[str, str]]:
        lines = text.split('\n')
        total_lines = len(lines)
        
        sections = self.find_major_sections(text)
        
        chunks = []
        
        if len(sections) >= 2:
            third = total_lines // 3
            
            first_boundary = min([s[1] for s in sections if third * 0.8 <= s[1] <= third * 1.5], 
                               default=third)
            second_boundary = min([s[1] for s in sections if third * 2 * 0.8 <= s[1] <= third * 2 * 1.5], 
                                default=third * 2)
            
            chunk1_text = '\n'.join(lines[:first_boundary])
            chunk2_text = '\n'.join(lines[first_boundary:second_boundary])
            chunk3_text = '\n'.join(lines[second_boundary:])
            
            chunk1_topic = sections[0][0] if sections else chapter_name + " - Introduction"
            chunk2_topic = next((s[0] for s in sections if s[1] >= first_boundary), chapter_name + " - Clinical Features")
            chunk3_topic = next((s[0] for s in sections if s[1] >= second_boundary), chapter_name + " - Management")
            
            chunks = [
                (chunk1_topic, chunk1_text),
                (chunk2_topic, chunk2_text),
                (chunk3_topic, chunk3_text)
            ]
        else:
            third = total_lines // 3
            chunk1_text = '\n'.join(lines[:third])
            chunk2_text = '\n'.join(lines[third:third*2])
            chunk3_text = '\n'.join(lines[third*2:])
            
            chunks = [
                (f"{chapter_name} - Part 1", chunk1_text),
                (f"{chapter_name} - Part 2", chunk2_text),
                (f"{chapter_name} - Part 3", chunk3_text)
            ]
        
        return chunks
    
    def extract_clinical_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        clinical_keywords = [
            'treatment', 'diagnosis', 'symptoms', 'clinical', 'management', 'therapy',
            'pathogenesis', 'etiology', 'patient', 'disease', 'disorder', 'syndrome',
            'incidence', 'prevalence', 'risk', 'complications', 'prognosis', 'outcome',
            'manifestations', 'presentation', 'findings', 'test', 'laboratory', 'imaging'
        ]
        
        scored_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 20 or len(sent) > 400:
                continue
            
            score = 0
            sent_lower = sent.lower()
            for keyword in clinical_keywords:
                if keyword in sent_lower:
                    score += 1
            
            if any(char.isdigit() for char in sent):
                score += 0.5
            
            if re.search(r'\d+%|\d+/\d+|p\s*[<>=]', sent):
                score += 1
            
            scored_sentences.append((score, sent))
        
        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        
        return [sent for score, sent in scored_sentences[:10]]
    
    def generate_summary_improved(self, text: str) -> str:
        clinical_sentences = self.extract_clinical_sentences(text)
        
        if not clinical_sentences:
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
            clinical_sentences = sentences[:5]
        
        summary_parts = []
        char_count = 0
        
        for sent in clinical_sentences:
            if char_count + len(sent) > 600:
                break
            summary_parts.append(sent)
            char_count += len(sent) + 2
        
        if len(summary_parts) < 3 and len(clinical_sentences) >= 3:
            summary_parts = clinical_sentences[:3]
        
        summary = '. '.join([s.rstrip('.') for s in summary_parts])
        
        if not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    def process_all_chapters(self) -> List[Dict]:
        self.chapters = self.parse_content_table()
        self.chapter_texts = self.extract_chapter_texts()
        
        dataset = []
        processed = 0
        
        for chapter_info in self.chapters:
            chapter_num = chapter_info['chapter_number']
            chapter_name = chapter_info['chapter_name']
            
            chapter_text = self.chapter_texts.get(chapter_name, '')
            
            if not chapter_text or len(chapter_text) < 100:
                print(f"Warning: Chapter {chapter_num} '{chapter_name}' has insufficient text. Skipping.")
                continue
            
            cleaned_text = self.clean_text(chapter_text)
            
            chunks = self.split_into_chunks(cleaned_text, chapter_name)
            
            for topic_name, content in chunks:
                if len(content.strip()) < 50:
                    content = cleaned_text[:2000]
                
                summary = self.generate_summary_improved(content)
                
                row = {
                    'book_title': BOOK_TITLE,
                    'chapter_number': chapter_num,
                    'chapter_name': chapter_name,
                    'topic_name': topic_name,
                    'content': content.strip(),
                    'summary': summary
                }
                dataset.append(row)
            
            processed += 1
            if processed % 50 == 0:
                print(f"Processed {processed}/{len(self.chapters)} chapters...")
        
        print(f"Total chunks created: {len(dataset)}")
        return dataset
    
    def save_to_csv(self, dataset: List[Dict], output_path: str):
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['book_title', 'chapter_number', 'chapter_name', 'topic_name', 'content', 'summary']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dataset)
        print(f"Dataset saved to {output_path}")
    
    def save_to_json(self, dataset: List[Dict], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset saved to {output_path}")

def main():
    content_table_path = '/project/workspace/nelson_pediatrics_content_table.txt'
    main_text_path = '/project/workspace/nelson_pediatrics.txt'
    
    extractor = NelsonDatasetExtractor(content_table_path, main_text_path)
    
    print("Starting dataset extraction with improved summaries...")
    print("=" * 60)
    
    dataset = extractor.process_all_chapters()
    
    extractor.save_to_csv(dataset, '/project/workspace/nelson_pediatrics_dataset_final.csv')
    extractor.save_to_json(dataset, '/project/workspace/nelson_pediatrics_dataset_final.json')
    
    print("=" * 60)
    print("Extraction complete!")
    print(f"Total chapters: {len(extractor.chapters)}")
    print(f"Total chunks: {len(dataset)}")
    print(f"Expected chunks per chapter: 3")
    print(f"Average chunks per chapter: {len(dataset) / len(extractor.chapters):.2f}")
    
    print("\n" + "=" * 60)
    print("Sample output:")
    print("=" * 60)
    for i, row in enumerate(dataset[:3], 1):
        print(f"\nSample {i}:")
        print(f"  Chapter: {row['chapter_number']} - {row['chapter_name']}")
        print(f"  Topic: {row['topic_name']}")
        print(f"  Content length: {len(row['content'])} chars")
        print(f"  Summary: {row['summary'][:200]}...")

if __name__ == '__main__':
    main()
