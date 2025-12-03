#!/usr/bin/env python3
"""
Add embeddings to existing Nelson Pediatrics enhanced dataset.
Run this after installing: pip install sentence-transformers
"""

import csv
import json
import sys
from typing import List, Optional

def load_embedding_model():
    """Load the BGE embedding model."""
    try:
        from sentence_transformers import SentenceTransformer
        print("Loading BGE-small-en-v1.5 model...")
        model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        print("✓ Model loaded successfully")
        return model
    except ImportError:
        print("ERROR: sentence-transformers not installed")
        print("Run: pip install sentence-transformers")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR loading model: {e}")
        sys.exit(1)

def generate_embedding(model, text: str) -> List[float]:
    """Generate embedding for text."""
    text_truncated = text[:512]  # Truncate to model limits
    embedding = model.encode(text_truncated, convert_to_numpy=True)
    return embedding.tolist()

def add_embeddings_to_dataset(input_path: str, output_path: str):
    """Add embeddings to all rows in the dataset."""
    
    # Load model
    model = load_embedding_model()
    
    # Read existing data
    print(f"\nReading dataset from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Found {len(rows)} rows to process")
    
    # Process each row
    print("\nGenerating embeddings...")
    for i, row in enumerate(rows, 1):
        # Generate embeddings
        content_emb = generate_embedding(model, row['content'][:1000])
        summary_emb = generate_embedding(model, row['summary'])
        topic_emb = generate_embedding(model, row['topic_name'])
        
        # Update row
        row['content_embedding'] = json.dumps(content_emb)
        row['summary_embedding'] = json.dumps(summary_emb)
        row['topic_embedding'] = json.dumps(topic_emb)
        
        if i % 100 == 0:
            print(f"  Processed {i}/{len(rows)} rows...")
    
    # Save updated dataset
    print(f"\nSaving updated dataset to {output_path}...")
    fieldnames = list(rows[0].keys())
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print("✓ Embeddings added successfully!")
    print(f"\nDataset saved to: {output_path}")
    print(f"Total embeddings generated: {len(rows) * 3}")
    print("  - Content embeddings: {len(rows)}")
    print("  - Summary embeddings: {len(rows)}")
    print("  - Topic embeddings: {len(rows)}")

def main():
    input_path = '/project/workspace/nelson_pediatrics_enhanced.csv'
    output_path = '/project/workspace/nelson_pediatrics_enhanced_with_embeddings.csv'
    
    print("="*70)
    print("NELSON PEDIATRICS - EMBEDDING GENERATOR")
    print("="*70)
    print("\nThis script adds semantic embeddings to the enhanced dataset.")
    print("Model: BGE-small-en-v1.5 (384 dimensions)")
    print(f"\nInput:  {input_path}")
    print(f"Output: {output_path}")
    print("="*70)
    
    try:
        add_embeddings_to_dataset(input_path, output_path)
        
        print("\n" + "="*70)
        print("✅ SUCCESS - Dataset is now RAG-ready!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Use the embedded dataset for semantic search")
        print("  2. Integrate with LangChain/LlamaIndex")
        print("  3. Build your RAG application")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
