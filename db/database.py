"""
DentAI Database Setup
=====================
SQLAlchemy modelleri ve veritabanı konfigürasyonu.
Streamlit uygulaması için SQLite kullanır.
"""

import datetime
import os
import sqlite3
from urllib.parse import urlparse
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==================== VERİTABANI KONFIGÜRASYONU ====================

# SQLite veritabanı URL'i (proje kök dizininde oluşturulacak)
DATABASE_URL = "sqlite:///./dentai_app.db"

# Engine oluştur (Streamlit için check_same_thread=False kritik!)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # True yaparsanız SQL sorgularını görebilirsiniz (debug için)
)

# Session factory (her veritabanı işlemi için yeni session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base (tüm modeller bundan türeyecek)
Base = declarative_base()


# ==================== VERİTABANI MODELLERİ ====================

class StudentSession(Base):
    """
    Öğrenci Oturumu Tablosu
    -----------------------
    Her öğrencinin bir vaka üzerindeki çalışma oturumunu takip eder.
    """
    __tablename__ = "student_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, nullable=False, index=True)  # Öğrenci kimliği
    case_id = Column(String, nullable=False)  # Hangi vaka üzerinde çalışıyor
    current_score = Column(Float, default=0.0)  # Anlık puan
    # Simulation state (JSON string). Stores patient context, revealed findings, progress, etc.
    state_json = Column(Text, default="{}")
    start_time = Column(DateTime, default=datetime.datetime.utcnow)  # Oturum başlangıç zamanı

    # İlişki: Bir oturumun birden fazla chat mesajı olabilir
    chat_logs = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudentSession(id={self.id}, student={self.student_id}, case={self.case_id}, score={self.current_score})>"


class ChatLog(Base):
    """
    Sohbet Geçmişi Tablosu
    ----------------------
    Öğrenci-AI arasındaki tüm mesajları kaydeder.
    MedGemma validasyon sonuçlarını metadata_json alanında saklar.
    """
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False)  # Hangi oturuma ait
    role = Column(String, nullable=False)  # 'user', 'assistant', veya 'system_validator'
    content = Column(Text, nullable=False)  # Mesaj içeriği
    metadata_json = Column(JSON, nullable=True)  # MedGemma analiz sonuçları (JSON formatında)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)  # Mesaj zamanı

    # İlişki: Her chat log bir oturuma aittir
    session = relationship("StudentSession", back_populates="chat_logs")

    def __repr__(self):
        return f"<ChatLog(id={self.id}, session_id={self.session_id}, role={self.role})>"


class ExamResult(Base):
    """
    Sınav Sonuçları Tablosu
    ------------------------
    Öğrencilerin tamamlanan vaka sonuçlarını ve detaylı skorlarını saklar.
    """
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # Öğrenci kimliği
    case_id = Column(String, nullable=False, index=True)  # Hangi vaka
    score = Column(Integer, nullable=False)  # Elde edilen puan
    max_score = Column(Integer, nullable=False)  # Maksimum olası puan
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)  # Tamamlanma zamanı
    details_json = Column(Text, nullable=True)  # Detaylı breakdown (JSON string)

    def __repr__(self):
        return f"<ExamResult(id={self.id}, user={self.user_id}, case={self.case_id}, score={self.score}/{self.max_score})>"


# ==================== VERİTABANI FONKSİYONLARI ====================

def init_db():
    """
    Veritabanını başlat (tüm tabloları oluştur).
    Uygulama ilk çalıştırıldığında çağrılmalı.
    """
    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite "migration": ensure new columns exist on existing DBs.
    # (SQLite's create_all does not alter existing tables.)
    try:
        _ensure_student_sessions_state_json_column()
    except Exception as e:
        # Don't hard-fail app startup; log for visibility.
        print(f"⚠️ Failed to ensure state_json column exists: {e}")


def _sqlite_db_file_path() -> Optional[str]:
    """Resolve the SQLite file path from DATABASE_URL (sqlite:///./file.db)."""
    try:
        parsed = urlparse(DATABASE_URL)
        if parsed.scheme != "sqlite":
            return None

        # sqlite:///./dentai_app.db -> path like /./dentai_app.db
        path = parsed.path
        if not path:
            return None

        # Strip leading '/' on Windows paths like '/./dentai_app.db'
        while path.startswith("/"):
            path = path[1:]

        # DATABASE_URL is relative to project root in this repo.
        return os.path.normpath(path)
    except Exception:
        return None


def _ensure_student_sessions_state_json_column() -> None:
    """Add student_sessions.state_json if missing (SQLite ALTER TABLE ADD COLUMN)."""
    db_file = _sqlite_db_file_path()
    if not db_file:
        return

    con = sqlite3.connect(db_file)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(student_sessions)")
        cols = [r[1] for r in cur.fetchall()]
        if "state_json" in cols:
            return

        cur.execute("ALTER TABLE student_sessions ADD COLUMN state_json TEXT DEFAULT '{}' ")
        con.commit()
    finally:
        con.close()


def get_db():
    """
    Veritabanı session generator (Dependency Injection için).
    
    Kullanım örneği:
    ---------------
    db = next(get_db())
    try:
        # Veritabanı işlemleri
        db.add(new_session)
        db.commit()
    finally:
        db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== TEST BLOĞU ====================

if __name__ == "__main__":
    """
    Bu dosyayı doğrudan çalıştırarak veritabanını oluşturabilirsiniz:
    python app/db/database.py
    """
    print("🚀 Veritabanı oluşturuluyor...")
    init_db()
    print("✅ Database created successfully!")
    print(f"📁 Dosya konumu: {DATABASE_URL}")
    
    # Test: Örnek bir session oluştur
    db = SessionLocal()
    try:
        test_session = StudentSession(
            student_id="test_student_001",
            case_id="olp_001",
            current_score=0.0
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        
        print(f"✅ Test session oluşturuldu: {test_session}")
        
        # Test: Örnek bir chat log ekle
        test_chat = ChatLog(
            session_id=test_session.id,
            role="user",
            content="Hastanın tıbbi geçmişini öğrenmek istiyorum.",
            metadata_json=None
        )
        db.add(test_chat)
        db.commit()
        
        print(f"✅ Test chat log oluşturuldu: {test_chat}")
        print("\n🎉 Veritabanı testi başarılı!")
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== HELPER FUNCTIONS ====================

def save_exam_result(user_id: str, case_id: str, score: int, max_score: int, details: dict = None):
    """
    Save completed exam result to database.
    
    Args:
        user_id: Student identifier
        case_id: Case identifier
        score: Points earned
        max_score: Maximum possible points
        details: Additional breakdown info (optional)
    
    Returns:
        ExamResult object or None if error
    """
    import json
    
    db = SessionLocal()
    try:
        result = ExamResult(
            user_id=user_id,
            case_id=case_id,
            score=score,
            max_score=max_score,
            details_json=json.dumps(details) if details else None
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result
    except Exception as e:
        print(f"Error saving exam result: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def get_user_stats(user_id: str):
    """
    Get comprehensive statistics for a user.
    
    Args:
        user_id: Student identifier
    
    Returns:
        dict with keys:
            - total_solved: Number of completed cases
            - avg_score: Average score percentage
            - user_level: Level based on performance
            - total_points: Total points earned
            - case_breakdown: List of individual case results
    """
    db = SessionLocal()
    try:
        # Get all exam results for this user
        results = db.query(ExamResult).filter_by(user_id=user_id).all()
        
        if not results:
            return {
                "total_solved": 0,
                "avg_score": 0,
                "user_level": "Başlangıç",
                "total_points": 0,
                "case_breakdown": []
            }
        
        # Calculate stats
        total_solved = len(results)
        total_points = sum(r.score for r in results)
        total_max = sum(r.max_score for r in results)
        avg_score = int((total_points / total_max * 100)) if total_max > 0 else 0
        
        # Determine user level
        if avg_score >= 90:
            user_level = "Uzman"
        elif avg_score >= 75:
            user_level = "İleri"
        elif avg_score >= 60:
            user_level = "Orta"
        else:
            user_level = "Başlangıç"
        
        # Case breakdown
        case_breakdown = [
            {
                "case_id": r.case_id,
                "score": r.score,
                "max_score": r.max_score,
                "percentage": int(r.score / r.max_score * 100) if r.max_score > 0 else 0,
                "completed_at": r.completed_at.strftime("%Y-%m-%d %H:%M")
            }
            for r in results
        ]
        
        return {
            "total_solved": total_solved,
            "avg_score": avg_score,
            "user_level": user_level,
            "total_points": total_points,
            "case_breakdown": case_breakdown
        }
    
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {
            "total_solved": 0,
            "avg_score": 0,
            "user_level": "Başlangıç",
            "total_points": 0,
            "case_breakdown": []
        }
    finally:
        db.close()


def get_student_detailed_history(user_id: str):
    """
    Get detailed action history for a student for analytics.
    This replaces the inline load_student_stats() logic in pages/5_stats.py.
    
    Args:
        user_id: Student identifier
    
    Returns:
        dict with keys:
            - action_history: List of action records with timestamp, case_id, action, score, outcome
            - total_score: Sum of all scores
            - total_actions: Count of actions
            - completed_cases: Set of unique case IDs
    """
    import json
    
    db = SessionLocal()
    try:
        # Get all sessions for this student
        sessions = db.query(StudentSession).filter_by(student_id=user_id).all()
        
        if not sessions:
            return {
                "action_history": [],
                "total_score": 0,
                "total_actions": 0,
                "completed_cases": set()
            }
        
        action_history = []
        total_score = 0
        total_actions = 0
        completed_cases = set()
        
        for session in sessions:
            # Get chat logs for this session (only assistant messages have evaluation metadata)
            logs = db.query(ChatLog).filter_by(
                session_id=session.id,
                role="assistant"
            ).all()
            
            for log in logs:
                if log.metadata_json:
                    try:
                        # Parse metadata
                        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else json.loads(log.metadata_json)
                        
                        # Extract action info
                        interpreted_action = metadata.get("interpreted_action", "unknown")
                        assessment = metadata.get("assessment", {})
                        score = assessment.get("score", 0)
                        outcome = assessment.get("rule_outcome", "N/A")
                        
                        # Only count if it's an ACTION (not general chat)
                        if interpreted_action and interpreted_action not in ["general_chat", "error"]:
                            action_record = {
                                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A",
                                "case_id": metadata.get("case_id", session.case_id),
                                "action": interpreted_action,
                                "score": score,
                                "outcome": outcome
                            }
                            action_history.append(action_record)
                            total_score += score
                            total_actions += 1
                            completed_cases.add(session.case_id)
                    
                    except Exception as e:
                        print(f"Error parsing metadata: {e}")
                        continue
        
        return {
            "action_history": action_history,
            "total_score": total_score,
            "total_actions": total_actions,
            "completed_cases": completed_cases
        }
    
    except Exception as e:
        print(f"Database error in get_student_detailed_history: {e}")
        return {
            "action_history": [],
            "total_score": 0,
            "total_actions": 0,
            "completed_cases": set()
        }
    finally:
        db.close()
 