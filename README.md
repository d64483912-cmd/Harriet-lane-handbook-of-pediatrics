# Nelson Pediatrics Dataset Creator

This tool extracts structured, clinically accurate data from **Nelson Textbook of Pediatrics** using the chapter structure defined in the content table.

## 📋 Features

- ✅ Extracts exactly **3 chunks per chapter**
- ✅ Maps chapters using `nelson_pediatrics_content_table.txt`
- ✅ Cleans text (removes artifacts, page numbers, hyphenation)
- ✅ Generates clinical summaries (3-5 sentences)
- ✅ Outputs to both CSV and JSON formats

## 📊 Output Columns

Each row contains:
1. **book_title** - Always "Nelson Textbook of Pediatrics"
2. **chapter_number** - From content table (line number)
3. **chapter_name** - From content table
4. **topic_name** - Extracted from chunk headings
5. **content** - Cleaned chunk text
6. **summary** - Concise clinical summary (3-5 sentences)

## 🚀 Usage

### Quick Start

```bash
python process_nelson_pediatrics.py
```

### Required Files

Ensure these files are in the same directory:
- `nelson_pediatrics.txt` - Full chapter text
- `nelson_pediatrics_content_table.txt` - Table of contents

### Output Files

- `nelson_pediatrics_dataset.csv` - CSV format
- `nelson_pediatrics_dataset.json` - JSON format

## 🧩 How It Works

### 1. Content Table Parsing
- Reads chapter names and page numbers from content table
- Assigns sequential chapter numbers based on table order

### 2. Chapter Extraction
- Locates chapter boundaries using page markers
- Extracts complete chapter text

### 3. Text Cleaning
- Removes download/copyright notices
- Removes page numbers and headers
- Fixes line-break hyphenation
- Cleans excessive whitespace

### 4. Chunk Creation (3 per chapter)
- Identifies section headings
- Splits logically by major topics
- Ensures coherent, meaningful segments

### 5. Topic Extraction
- Extracts first major heading from chunk
- Falls back to chapter name if no heading found

### 6. Summary Generation
- Selects key sentences from beginning, middle, end
- Produces 3-5 sentence clinical summaries
- Filters out artifacts and references

## 📈 Example Output

```csv
book_title,chapter_number,chapter_name,topic_name,content,summary
"Nelson Textbook of Pediatrics",1,"Overview of Pediatrics","Introduction to Pediatric Medicine","...","Pediatrics focuses on the health and development of children..."
```

## ⚙️ Technical Details

- **Language**: Python 3.12.8
- **Dependencies**: None (uses standard library only)
- **Processing Time**: ~2-5 minutes (depending on file size)
- **Memory**: Processes chapters sequentially to minimize memory usage

## ✅ Validation

The script ensures:
- Every chapter has exactly 3 chunks
- No fabricated metadata
- Chapter numbers match content table
- Summaries are factual and clinically relevant
- All required columns are populated

## 🔧 Customization

You can modify the script to:
- Change number of chunks per chapter (default: 3)
- Adjust summary length (default: 3-5 sentences)
- Customize text cleaning rules
- Change output formats

## 📝 Notes

- Chapters with minimal content receive placeholder entries
- Topic names are extracted from actual text, never fabricated
- Summaries capture clinical essence without citations
- All cleaning preserves medical terminology and clinical data
