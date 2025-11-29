# Optional helper to seed a candidate for testing (run once)
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import Candidate, Question, Test, Answer

load_dotenv()
Base.metadata.create_all(bind=engine)

def seed():
    db: Session = SessionLocal()
    try:
        email = os.getenv("SEED_EMAIL", "test.candidate@example.com")
        name = os.getenv("SEED_NAME", "Test Candidate")
        c = db.execute(select(Candidate).where(Candidate.email == email)).scalar_one_or_none()
        if not c:
            c = Candidate(name=name, email=email, authorized=True)
            db.add(c); db.commit()
            print("Seeded candidate", email)
        else:
            print("Candidate already exists:", email)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
