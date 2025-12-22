"""
Database Initialization Script
===============================
Creates all required database tables if they don't exist.
Run this script when setting up the project for the first time.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --recreate
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from db.database import init_db, SessionLocal, StudentSession, ExamResult
import datetime


def setup_database():
    """Initialize database and create all tables"""
    print("=" * 60)
    print("DATABASE INITIALIZATION")
    print("=" * 60)
    
    try:
        recreate = "--recreate" in sys.argv or os.getenv("DENTAI_RECREATE_DB") == "1"

        # SQLite file lives at project root: ./dentai_app.db
        db_path = project_root / "dentai_app.db"
        if recreate and db_path.exists():
            print("\n🧹 Recreate requested: deleting existing dentai_app.db...")
            db_path.unlink()

        # Create all tables
        print("\n📦 Creating database tables...")
        init_db()
        print("✅ Tables created successfully!")
        
        # List created tables
        print("\n📋 Created tables:")
        print("  - student_sessions")
        print("  - chat_logs")
        print("  - exam_results")
        
        # Verify database
        print("\n🔍 Verifying database connection...")
        db = SessionLocal()
        try:
            # Test query
            count = db.query(StudentSession).count()
            print(f"✅ Database connection OK (Sessions: {count})")
        finally:
            db.close()

        # Verify schema includes state_json
        if db_path.exists():
            try:
                con = sqlite3.connect(str(db_path))
                cur = con.cursor()
                cur.execute("PRAGMA table_info(student_sessions)")
                cols = [r[1] for r in cur.fetchall()]  # (cid, name, type, notnull, dflt_value, pk)
                con.close()

                if "state_json" not in cols:
                    print("\n⚠️  WARNING: student_sessions.state_json column is missing.")
                    print("   SQLite cannot auto-migrate columns via create_all().")
                    print("   Options:")
                    print("   - Recreate DB: python scripts/init_db.py --recreate")
                    print("   - Or delete dentai_app.db and rerun init_db")
                else:
                    print("✅ Schema OK: state_json column present")
            except Exception as e:
                print(f"\n⚠️  Could not verify schema via PRAGMA: {e}")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print("\nYou can now run the Streamlit app:")
        print("  streamlit run main.py")
        
    except Exception as e:
        print(f"\n❌ Error during database setup: {e}")
        raise


if __name__ == "__main__":
    setup_database()
