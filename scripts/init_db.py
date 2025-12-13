"""
Database Initialization Script
===============================
Creates all required database tables if they don't exist.
Run this script when setting up the project for the first time.

Usage:
    python scripts/init_db.py
"""

import sys
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
