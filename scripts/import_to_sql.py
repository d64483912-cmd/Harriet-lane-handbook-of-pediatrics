#!/usr/bin/env python3
"""
Import Nelson Pediatrics dataset to SQL database
Supports PostgreSQL, MySQL, and SQLite
"""

import csv
import sqlite3
import argparse
from pathlib import Path


def import_to_sqlite(csv_file: str, db_file: str = 'nelson_pediatrics.db'):
    """Import CSV data to SQLite database"""
    print(f"📦 Importing {csv_file} to SQLite database: {db_file}")
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pediatrics_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_title TEXT NOT NULL,
        chapter_number INTEGER NOT NULL,
        chapter_name TEXT NOT NULL,
        topic_name TEXT,
        content TEXT NOT NULL,
        category TEXT,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chapter ON pediatrics_chunks(chapter_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON pediatrics_chunks(category)')
    
    # Import data
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows_imported = 0
        
        for row in reader:
            cursor.execute('''
            INSERT INTO pediatrics_chunks 
            (book_title, chapter_number, chapter_name, topic_name, content, category, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['book_title'],
                int(row['chapter_number']),
                row['chapter_name'],
                row['topic_name'],
                row['content'],
                row['category'],
                row['summary']
            ))
            rows_imported += 1
            
            if rows_imported % 100 == 0:
                print(f"  Imported {rows_imported} rows...")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully imported {rows_imported} rows to {db_file}")
    print(f"   Database size: {Path(db_file).stat().st_size / 1024 / 1024:.2f} MB")


def import_to_postgres(csv_file: str, connection_string: str):
    """Import CSV data to PostgreSQL database"""
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return
    
    print(f"📦 Importing {csv_file} to PostgreSQL...")
    
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open('sql_schema.sql', 'r') as f:
        schema = f.read()
        cursor.execute(schema)
    
    # Import data
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows_imported = 0
        
        for row in reader:
            cursor.execute('''
            INSERT INTO pediatrics_chunks 
            (book_title, chapter_number, chapter_name, topic_name, content, category, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                row['book_title'],
                int(row['chapter_number']),
                row['chapter_name'],
                row['topic_name'],
                row['content'],
                row['category'],
                row['summary']
            ))
            rows_imported += 1
            
            if rows_imported % 100 == 0:
                print(f"  Imported {rows_imported} rows...")
                conn.commit()
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully imported {rows_imported} rows to PostgreSQL")


def main():
    parser = argparse.ArgumentParser(description='Import Nelson Pediatrics dataset to SQL database')
    parser.add_argument('--csv', default='nelson_pediatrics_dataset_v2.csv', help='CSV file to import')
    parser.add_argument('--db-type', choices=['sqlite', 'postgres', 'mysql'], default='sqlite', help='Database type')
    parser.add_argument('--db-file', default='nelson_pediatrics.db', help='SQLite database file')
    parser.add_argument('--connection-string', help='PostgreSQL/MySQL connection string')
    
    args = parser.parse_args()
    
    if args.db_type == 'sqlite':
        import_to_sqlite(args.csv, args.db_file)
    elif args.db_type == 'postgres':
        if not args.connection_string:
            print("❌ PostgreSQL requires --connection-string")
            return
        import_to_postgres(args.csv, args.connection_string)
    else:
        print(f"❌ {args.db_type} import not yet implemented")


if __name__ == '__main__':
    main()
