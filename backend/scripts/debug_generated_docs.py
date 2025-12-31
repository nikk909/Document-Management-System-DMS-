# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.storage.database import get_db_session, GeneratedDocumentMetadata
from sqlalchemy import text

def check():
    try:
        with get_db_session() as db:
            docs = db.query(GeneratedDocumentMetadata).all()
            print(f"Total generated docs: {len(docs)}")
            for d in docs[:10]:
                print(f"ID: {d.id}, File: {d.filename}, Category: {d.category}, Status: {d.status}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()

