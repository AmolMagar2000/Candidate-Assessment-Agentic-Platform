from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = {"schema": "ats_candidates"}
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(Integer, nullable=True, unique=True) # For mapping to API ID
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    authorized = Column(Boolean, default=False)
    has_taken_test = Column(Boolean, default=False)
    role = Column(String(100), default="backend", nullable=False)
    tests = relationship("Test", back_populates="candidate")

class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "ats_assessments"} 
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(100), default="backend")  
    qtype = Column(String(50))  # 'mcq' or 'coding'
    difficulty = Column(String(50))  # 'easy', 'medium', 'hard'
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  
    correct_answer = Column(Integer, nullable=True)  
    test_cases = Column(JSON, nullable=True)  

class Test(Base):
    __tablename__ = "tests"
    __table_args__ = {"schema": "ats_assessments"} 
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("ats_candidates.candidates.id"), nullable=False)
    question_ids = Column(ARRAY(Integer), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    score_mcq = Column(Integer, default=0)
    score_coding = Column(Integer, default=0)
    total_score = Column(Integer, default=0)

    candidate = relationship("Candidate", back_populates="tests")
    answers = relationship("Answer", back_populates="test")

class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = {"schema": "ats_assessments"} 
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("ats_assessments.tests.id"), nullable=False)
    question_id = Column(Integer, nullable=False)
    response = Column(Text, nullable=True) 
    is_correct = Column(Boolean, nullable=True)

    test = relationship("Test", back_populates="answers")