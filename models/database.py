# models/database.py
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from config.settings import settings

# Database setup
engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Student(Base):
    """Student model for tracking individual learners"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    grade = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    
    # Relationships
    sessions = relationship("LearningSession", back_populates="student")
    assessments = relationship("Assessment", back_populates="student")
    achievements = relationship("Achievement", back_populates="student")

class LearningSession(Base):
    """Track individual learning sessions"""
    __tablename__ = "learning_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject = Column(String(50), nullable=False)
    topic = Column(String(100), nullable=False)
    subtopic = Column(String(100), nullable=False)
    session_type = Column(String(20), nullable=False)  # 'practice', 'assessment', 'explanation'
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)
    
    # Performance metrics
    questions_attempted = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    average_difficulty = Column(Float, default=1.0)
    points_earned = Column(Integer, default=0)
    
    # Session data
    session_data = Column(JSON)  # Store detailed session information
    
    # Relationships
    student = relationship("Student", back_populates="sessions")
    responses = relationship("QuestionResponse", back_populates="session")

class QuestionResponse(Base):
    """Track individual question responses"""
    __tablename__ = "question_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"))
    question_text = Column(Text, nullable=False)
    student_answer = Column(Text)
    correct_answer = Column(Text)
    is_correct = Column(Boolean, default=False)
    difficulty_level = Column(Integer, default=1)
    time_spent_seconds = Column(Integer)
    hint_used = Column(Boolean, default=False)
    feedback = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    session = relationship("LearningSession", back_populates="responses")

class Assessment(Base):
    """Track formal assessments"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject = Column(String(50), nullable=False)
    topic = Column(String(100), nullable=False)
    subtopic = Column(String(100), nullable=False)
    total_questions = Column(Integer, default=5)
    correct_answers = Column(Integer, default=0)
    score_percentage = Column(Float, default=0.0)
    completed_at = Column(DateTime, default=func.now())
    time_taken_minutes = Column(Integer)
    
    # Learning plan data
    strengths = Column(JSON)
    weaknesses = Column(JSON)
    recommendations = Column(Text)
    
    # Relationships
    student = relationship("Student", back_populates="assessments")

class Achievement(Base):
    """Track student achievements and badges"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    badge_name = Column(String(100), nullable=False)
    badge_description = Column(Text)
    earned_at = Column(DateTime, default=func.now())
    points_awarded = Column(Integer, default=0)
    
    # Relationships
    student = relationship("Student", back_populates="achievements")

class Topic(Base):
    """Track topic mastery levels"""
    __tablename__ = "topic_mastery"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject = Column(String(50), nullable=False)
    topic = Column(String(100), nullable=False)
    subtopic = Column(String(100), nullable=False)
    mastery_level = Column(Float, default=0.0)  # 0.0 to 1.0
    last_practiced = Column(DateTime, default=func.now())
    practice_count = Column(Integer, default=0)
    assessment_count = Column(Integer, default=0)

# Database utility functions
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_or_create_student(db: Session, name: str, grade: str) -> Student:
    """Get existing student or create new one"""
    student = db.query(Student).filter(
        Student.name == name, 
        Student.grade == grade
    ).first()
    
    if not student:
        student = Student(name=name, grade=grade)
        db.add(student)
        db.commit()
        db.refresh(student)
    else:
        # Update last active
        student.last_active = func.now()
        db.commit()
    
    return student

def save_learning_session(
    db: Session,
    student_id: int,
    subject: str,
    topic: str,
    subtopic: str,
    session_type: str,
    session_data: dict,
    questions_attempted: int = 0,
    questions_correct: int = 0,
    duration_minutes: int = 0
) -> LearningSession:
    """Save a learning session to database"""
    session = LearningSession(
        student_id=student_id,
        subject=subject,
        topic=topic,
        subtopic=subtopic,
        session_type=session_type,
        session_data=session_data,
        questions_attempted=questions_attempted,
        questions_correct=questions_correct,
        duration_minutes=duration_minutes,
        end_time=func.now()
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_student_progress(db: Session, student_id: int, subject: str) -> dict:
    """Get comprehensive student progress data"""
    # Get recent sessions
    recent_sessions = db.query(LearningSession).filter(
        LearningSession.student_id == student_id,
        LearningSession.subject == subject
    ).order_by(LearningSession.start_time.desc()).limit(10).all()
    
    # Get assessments
    assessments = db.query(Assessment).filter(
        Assessment.student_id == student_id,
        Assessment.subject == subject
    ).order_by(Assessment.completed_at.desc()).all()
    
    # Calculate overall performance
    total_questions = sum(s.questions_attempted for s in recent_sessions)
    total_correct = sum(s.questions_correct for s in recent_sessions)
    accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
    
    return {
        "recent_sessions": len(recent_sessions),
        "total_questions_attempted": total_questions,
        "accuracy_percentage": round(accuracy, 1),
        "recent_assessments": len(assessments),
        "last_session": recent_sessions[0].start_time if recent_sessions else None,
        "sessions": recent_sessions,
        "assessments": assessments
    }