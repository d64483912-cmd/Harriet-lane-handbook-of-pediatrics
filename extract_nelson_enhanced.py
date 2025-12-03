import re
import csv
import json
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
import math

BOOK_TITLE = "Nelson Textbook of Pediatrics"

class EnhancedNelsonExtractor:
    def __init__(self, content_table_path: str, main_text_path: str):
        self.content_table_path = content_table_path
        self.main_text_path = main_text_path
        self.chapters = []
        self.chapter_texts = {}
        self.embedding_model = None
        
    def initialize_embeddings(self):
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading embedding model (BGE-small-en-v1.5)...")
            self.embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
            print("✓ Embedding model loaded")
            return True
        except ImportError:
            print("⚠ sentence-transformers not installed. Run: pip install sentence-transformers")
            print("⚠ Continuing without embeddings...")
            return False
        except Exception as e:
            print(f"⚠ Could not load embedding model: {e}")
            return False
    
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
                            'chapter_id': f'NELSON-CH-{chapter_num:04d}',
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
        return text.strip()
    
    def extract_clinical_headings(self, text: str) -> List[Tuple[str, int]]:
        lines = text.split('\n')
        headings = []
        
        clinical_keywords = [
            'etiology', 'pathogenesis', 'clinical', 'diagnosis', 'treatment', 
            'management', 'therapy', 'epidemiology', 'symptoms', 'signs',
            'complications', 'prognosis', 'prevention', 'screening', 'manifestations'
        ]
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if len(line_stripped) == 0:
                continue
            
            if line_stripped.isupper() and 5 < len(line_stripped) < 100:
                headings.append((line_stripped, i, 3))
            elif re.match(r'^[A-Z][A-Za-z\s,\-:()]+$', line_stripped):
                if 10 < len(line_stripped) < 150:
                    if not any(kw in line_stripped.lower() for kw in ['chapter', 'page', 'downloaded', 'elsevier']):
                        score = 1
                        for keyword in clinical_keywords:
                            if keyword in line_stripped.lower():
                                score += 1
                        headings.append((line_stripped, i, score))
        
        headings.sort(key=lambda x: x[2], reverse=True)
        return headings
    
    def extract_tables(self, text: str) -> List[Dict]:
        tables = []
        
        table_pattern = r'Table\s+\d+[.\-]\d+[^\n]*\n((?:[^\n]+\n)+?)(?=\n\n|\Z)'
        matches = re.finditer(table_pattern, text, re.MULTILINE)
        
        for match in matches:
            table_title = match.group(0).split('\n')[0].strip()
            table_content = match.group(1).strip()
            
            rows = [row.strip() for row in table_content.split('\n') if row.strip()]
            
            if len(rows) >= 2:
                tables.append({
                    'title': table_title,
                    'rows': rows[:10],
                    'position': match.start()
                })
        
        return tables
    
    def extract_topic_name_intelligent(self, text: str, chapter_name: str, chunk_index: int) -> str:
        headings = self.extract_clinical_headings(text)
        
        if headings and headings[0][2] >= 2:
            return headings[0][0].title()
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if 20 < len(s) < 200]
        
        if sentences:
            first_sentence = sentences[0]
            
            clinical_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}\b', first_sentence)
            
            if clinical_terms:
                topic = ' '.join(clinical_terms[:3])
                if len(topic) > 10:
                    return topic
        
        words = re.findall(r'\b[a-z]{4,}\b', text[:1000].lower())
        
        stop_words = {'with', 'from', 'that', 'this', 'have', 'been', 'will', 'their', 
                     'more', 'than', 'these', 'other', 'such', 'into', 'were', 'also'}
        
        filtered_words = [w for w in words if w not in stop_words]
        
        if filtered_words:
            word_freq = Counter(filtered_words)
            top_words = [w for w, _ in word_freq.most_common(3)]
            topic = ' '.join(top_words).title()
            if len(topic) > 10:
                return f"{chapter_name}: {topic}"
        
        part_names = ['Introduction & Overview', 'Clinical Features & Management', 'Treatment & Outcomes']
        return f"{chapter_name} - {part_names[chunk_index]}"
    
    def split_into_clinical_chunks(self, text: str, chapter_name: str) -> List[Tuple[str, str, List[str]]]:
        lines = text.split('\n')
        total_lines = len(lines)
        
        headings = self.extract_clinical_headings(text)
        
        boundaries = []
        third = total_lines // 3
        
        if len(headings) >= 2:
            first_boundary = min(
                [h[1] for h in headings if third * 0.7 <= h[1] <= third * 1.3],
                default=third
            )
            second_boundary = min(
                [h[1] for h in headings if third * 2 * 0.7 <= h[1] <= third * 2 * 1.3],
                default=third * 2
            )
            boundaries = [0, first_boundary, second_boundary, total_lines]
        else:
            boundaries = [0, third, third * 2, total_lines]
        
        chunks = []
        for i in range(3):
            start = boundaries[i]
            end = boundaries[i + 1]
            
            chunk_lines = lines[start:end]
            
            while start > 0 and chunk_lines and len(chunk_lines[0].strip()) < 50:
                start += 1
                chunk_lines = lines[start:end]
            
            chunk_text = '\n'.join(chunk_lines)
            
            micro_chunks = self.create_micro_chunks(chunk_text)
            
            topic_name = self.extract_topic_name_intelligent(chunk_text, chapter_name, i)
            
            chunks.append((topic_name, chunk_text, micro_chunks))
        
        return chunks
    
    def create_micro_chunks(self, text: str) -> List[str]:
        paragraphs = text.split('\n\n')
        
        micro_chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            if current_length + para_length > 1000 and current_chunk:
                micro_chunks.append(' '.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        if current_chunk:
            micro_chunks.append(' '.join(current_chunk))
        
        return micro_chunks[:5]
    
    def calculate_tfidf_scores(self, text: str, corpus_freq: Dict[str, int]) -> Dict[str, float]:
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        
        word_freq = Counter(words)
        
        tfidf = {}
        for word, freq in word_freq.items():
            tf = freq / len(words)
            idf = math.log(1000 / (corpus_freq.get(word, 1) + 1))
            tfidf[word] = tf * idf
        
        return tfidf
    
    def generate_enhanced_summary(self, text: str, topic_name: str, chapter_name: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if 20 < len(s) < 500]
        
        if not sentences:
            return text[:300] + "..."
        
        clinical_keywords = {
            'diagnosis': 3, 'treatment': 3, 'management': 3, 'therapy': 2.5,
            'symptoms': 2, 'clinical': 2, 'patient': 2, 'disease': 2,
            'complication': 2.5, 'prognosis': 2.5, 'outcome': 2,
            'etiology': 2, 'pathogenesis': 2, 'manifestation': 2,
            'incidence': 1.5, 'prevalence': 1.5, 'risk': 1.5,
            'test': 1.5, 'laboratory': 1.5, 'imaging': 1.5
        }
        
        scored_sentences = []
        for sent in sentences:
            score = 0
            sent_lower = sent.lower()
            
            for keyword, weight in clinical_keywords.items():
                if keyword in sent_lower:
                    score += weight
            
            if re.search(r'\d+%|\d+/\d+|p\s*[<>=]|95%\s*CI', sent):
                score += 2
            
            if any(char.isdigit() for char in sent):
                score += 0.5
            
            if re.search(r'\bmg/kg\b|\bmg/dL\b|\bμmol/L\b|\byears?\b|\bmonths?\b', sent):
                score += 1.5
            
            if sent.startswith(('The', 'In', 'Treatment', 'Diagnosis', 'Management')):
                score += 0.5
            
            scored_sentences.append((score, sent))
        
        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        
        summary_sentences = []
        total_chars = 0
        
        for score, sent in scored_sentences:
            if total_chars + len(sent) > 600:
                break
            if len(summary_sentences) >= 5:
                break
            
            summary_sentences.append(sent)
            total_chars += len(sent)
        
        if len(summary_sentences) < 2:
            summary_sentences = [s for _, s in scored_sentences[:3]]
        
        summary = ' '.join(summary_sentences)
        
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        if not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        if not self.embedding_model:
            return None
        
        try:
            text_truncated = text[:512]
            embedding = self.embedding_model.encode(text_truncated, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"⚠ Embedding generation failed: {e}")
            return None
    
    def process_all_chapters(self) -> List[Dict]:
        self.chapters = self.parse_content_table()
        self.chapter_texts = self.extract_chapter_texts()
        
        dataset = []
        processed = 0
        
        for chapter_info in self.chapters:
            chapter_num = chapter_info['chapter_number']
            chapter_id = chapter_info['chapter_id']
            chapter_name = chapter_info['chapter_name']
            
            chapter_text = self.chapter_texts.get(chapter_name, '')
            
            if not chapter_text or len(chapter_text) < 100:
                print(f"⚠ Chapter {chapter_num} '{chapter_name}' has insufficient text. Skipping.")
                continue
            
            cleaned_text = self.clean_text(chapter_text)
            
            tables = self.extract_tables(cleaned_text)
            
            chunks = self.split_into_clinical_chunks(cleaned_text, chapter_name)
            
            for chunk_idx, (topic_name, content, micro_chunks) in enumerate(chunks):
                if len(content.strip()) < 50:
                    content = cleaned_text[:2000]
                
                summary = self.generate_enhanced_summary(content, topic_name, chapter_name)
                
                content_embedding = self.generate_embedding(content[:1000])
                summary_embedding = self.generate_embedding(summary)
                topic_embedding = self.generate_embedding(topic_name)
                
                row = {
                    'book_title': BOOK_TITLE,
                    'chapter_id': chapter_id,
                    'chapter_number': chapter_num,
                    'chapter_name': chapter_name,
                    'chunk_index': chunk_idx + 1,
                    'topic_name': topic_name,
                    'content': content.strip(),
                    'summary': summary,
                    'micro_chunks': json.dumps(micro_chunks),
                    'tables': json.dumps(tables) if tables else '[]',
                    'content_embedding': json.dumps(content_embedding) if content_embedding else '[]',
                    'summary_embedding': json.dumps(summary_embedding) if summary_embedding else '[]',
                    'topic_embedding': json.dumps(topic_embedding) if topic_embedding else '[]'
                }
                dataset.append(row)
            
            processed += 1
            if processed % 50 == 0:
                print(f"Processed {processed}/{len(self.chapters)} chapters...")
        
        print(f"✓ Total chunks created: {len(dataset)}")
        return dataset
    
    def save_to_csv(self, dataset: List[Dict], output_path: str):
        fieldnames = [
            'book_title', 'chapter_id', 'chapter_number', 'chapter_name', 
            'chunk_index', 'topic_name', 'content', 'summary', 
            'micro_chunks', 'tables', 'content_embedding', 
            'summary_embedding', 'topic_embedding'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dataset)
        print(f"✓ Dataset saved to {output_path}")
    
    def save_to_json(self, dataset: List[Dict], output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"✓ Dataset saved to {output_path}")

def main():
    content_table_path = '/project/workspace/nelson_pediatrics_content_table.txt'
    main_text_path = '/project/workspace/nelson_pediatrics.txt'
    
    print("="*70)
    print("NELSON PEDIATRICS ENHANCED EXTRACTION")
    print("="*70)
    print("\nFeatures:")
    print("  ✓ Intelligent topic name extraction")
    print("  ✓ Enhanced extractive-compressive summaries")
    print("  ✓ Clinical table extraction")
    print("  ✓ Hierarchical micro-chunking")
    print("  ✓ Stable chapter IDs")
    print("  ✓ Embeddings (BGE-small-en-v1.5)")
    print("="*70)
    
    extractor = EnhancedNelsonExtractor(content_table_path, main_text_path)
    
    extractor.initialize_embeddings()
    
    print("\nStarting extraction...")
    dataset = extractor.process_all_chapters()
    
    extractor.save_to_csv(dataset, '/project/workspace/nelson_pediatrics_enhanced.csv')
    extractor.save_to_json(dataset, '/project/workspace/nelson_pediatrics_enhanced.json')
    
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE!")
    print("="*70)
    print(f"  Total chapters: {len(extractor.chapters)}")
    print(f"  Total chunks: {len(dataset)}")
    print(f"  Average chunks per chapter: {len(dataset) / len(extractor.chapters):.2f}")
    print(f"  Embeddings: {'✓ Included' if extractor.embedding_model else '✗ Not generated'}")
    print("="*70)

if __name__ == '__main__':
    main()
