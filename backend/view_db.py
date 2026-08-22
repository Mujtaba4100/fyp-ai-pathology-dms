import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal

def view_database():
    db = SessionLocal()
    print("=" * 80)
    print("  POSTGRESQL DATABASE CONTENTS VIEW (Docker: emr_postgres)")
    print("=" * 80)

    try:
        # 1. Documents
        print("\n--- 1. DOCUMENTS TABLE ---")
        docs = db.execute(text("SELECT id, file_id, filename, file_size, file_type, upload_date, ocr_status, extraction_status, LENGTH(file_data) as file_bytes FROM documents ORDER BY id DESC")).fetchall()
        if docs:
            for d in docs:
                print(f"ID: {d.id} | FileID: {d.file_id} | Name: {d.filename} | Type: {d.file_type} | Size: {d.file_size} bytes | Uploaded: {d.upload_date} | OCR Status: {d.ocr_status} | Extracted File Bytes: {d.file_bytes or 0}")
        else:
            print("  (No documents uploaded yet)")

        # 2. Pathology Reports
        print("\n--- 2. PATHOLOGY REPORTS TABLE ---")
        reports = db.execute(text("SELECT id, document_id, patient_id, patient_name, test_type, summary, created_at FROM pathology_reports ORDER BY id DESC")).fetchall()
        if reports:
            for r in reports:
                print(f"ID: {r.id} | DocID: {r.document_id} | Patient: {r.patient_name or 'N/A'} (ID: {r.patient_id or 'N/A'}) | Test: {r.test_type} | Summary: {r.summary[:80] if r.summary else 'N/A'}...")
        else:
            print("  (No pathology reports saved yet)")

        # 3. Document Embeddings
        print("\n--- 3. DOCUMENT EMBEDDINGS TABLE ---")
        embeddings = db.execute(text("SELECT id, document_id, text_chunk, created_at FROM document_embeddings ORDER BY id DESC")).fetchall()
        if embeddings:
            for e in embeddings:
                print(f"ID: {e.id} | DocID: {e.document_id} | Chunk Snippet: {e.text_chunk[:80]}...")
        else:
            print("  (No embeddings stored yet)")

        # 4. Users
        print("\n--- 4. USERS TABLE ---")
        users = db.execute(text("SELECT id, username, email, role, is_active, created_at FROM users ORDER BY id DESC")).fetchall()
        if users:
            for u in users:
                print(f"ID: {u.id} | Username: {u.username} | Email: {u.email} | Role: {u.role} | Active: {u.is_active}")
        else:
            print("  (No users in SQL table)")

    except Exception as err:
        print(f"[ERROR] Query failed: {err}")
    finally:
        db.close()
    print("=" * 80)

if __name__ == "__main__":
    view_database()
