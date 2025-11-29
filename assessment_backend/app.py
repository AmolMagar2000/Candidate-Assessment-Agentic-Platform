from code_executor import CodeExecutor
import os, random, asyncio, logging, httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from dotenv import load_dotenv
from db import Base, engine, get_db
from models import Candidate, Question, Test, Answer
from schemas import CandidateAuth, StartTestResponse, SubmitPayload
from llm import generate_mcq_questions, generate_coding_questions
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

MCQ_LIMIT = 10 
CODING_LIMIT = 3
EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL")

app = FastAPI(title="Assessment Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
code_executor = CodeExecutor()

def normalize_role(api_role_name: str | None) -> str:
    if not api_role_name: return "backend"
    name = api_role_name.lower().strip()
    if "apex" in name: return "apex"
    if "react" in name: return "react"
    if "java" in name: return "java"
    if "oic" in name: return "oic"
    return "backend"

@app.get("/admin/sync-external-candidates")
async def sync_external_candidates(db: Session = Depends(get_db)):
    logger.info("🔄 Syncing candidates from external API...")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(EXTERNAL_API_URL, timeout=10)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="External API Error")
            data = resp.json() 
        
        added = 0
        updated = 0
        
        for item in data:
            try:
                email = item.get('cEmail')
                if not email: continue
                
                role = normalize_role(item['candidateRole'].get('role_name'))
                
                existing = db.execute(select(Candidate).where(Candidate.email == email)).scalar_one_or_none()
                
                if existing:
                    if existing.external_id != item.get('candidateId') or existing.role != role:
                        existing.external_id = item.get('candidateId')
                        existing.role = role
                        updated += 1
                else:
                    db.add(Candidate(
                        name=item['name'],
                        email=email,
                        external_id=item.get('candidateId'),
                        role=role,
                        authorized=False
                    ))
                    added += 1
            except Exception as e:
                logger.warning(f"Skipping item: {e}")
                continue
        
        db.commit()
        return {"status": "success", "added": added, "updated": updated}

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/candidates")
def get_candidates(db: Session = Depends(get_db)):
    return db.execute(select(Candidate).order_by(Candidate.id.desc())).scalars().all()

@app.post("/admin/authorize")
def authorize_candidate(payload: CandidateAuth, db: Session = Depends(get_db)):
    c = db.execute(select(Candidate).where(Candidate.email == payload.email)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    c.authorized = True
    db.commit()
    return {"email": c.email, "authorized": c.authorized}

@app.post("/admin/generate-mcq")
async def admin_generate_mcq(role: str = Body(...), mcq_count: int = Body(15), db: Session = Depends(get_db)):
    normalized_role = normalize_role(role)
    try:
        # Directly call generation (verification layer removed inside llm.py)
        data = await generate_mcq_questions(role=normalized_role, mcq_count=mcq_count)
        mcqs = data.get("mcqs", [])
        created = 0
        
        for q in mcqs:
            if not isinstance(q, dict):
                logger.warning(f"Skipping invalid question format: {q}")
                continue
                
            db.add(Question(
                role=normalized_role,
                qtype="mcq",
                difficulty="hard",
                question_text=q["question"],
                options=q.get("options"),
                correct_answer=q.get("correct_answer", 0),
            ))
            created += 1
            
        db.commit()
        return {"created": created, "role": normalized_role}
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/generate-coding")
async def admin_generate_coding(role: str = Body(...), coding_count: int = Body(5), db: Session = Depends(get_db)):
    normalized_role = normalize_role(role)
    try:
        data = await generate_coding_questions(role=normalized_role, coding_count=coding_count)
        coding = data.get("coding", [])
        created = 0
        
        for q in coding:
            if not isinstance(q, dict):
                logger.warning(f"Skipping invalid coding question format: {q}")
                continue

            db.add(Question(
                role=normalized_role,
                qtype="coding",
                difficulty="hard",
                question_text=q["question"],
                test_cases=q.get("test_cases"),
                options=q.get("options"),
                correct_answer=q.get("correct_answer")
            ))
            created += 1
        
        db.commit()
        return {"created": created, "role": normalized_role}
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-test", response_model=StartTestResponse)
def start_test(payload: CandidateAuth, db: Session = Depends(get_db)):
    c = db.execute(select(Candidate).where(Candidate.email == payload.email)).scalar_one_or_none()
    if not c or not c.authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    if c.has_taken_test:
        raise HTTPException(status_code=400, detail="Test already submitted")
    
    mcq_questions = db.execute(select(Question).where(Question.qtype == "mcq", Question.role == c.role)).scalars().all()
    coding_questions = db.execute(select(Question).where(Question.qtype == "coding", Question.role == c.role)).scalars().all()

    if len(mcq_questions) < MCQ_LIMIT:
        raise HTTPException(status_code=400, detail="Not enough questions generated.")
    
    # Random sampling
    chosen_mcqs = random.sample([q.id for q in mcq_questions], min(len(mcq_questions), MCQ_LIMIT))
    chosen_coding = random.sample([q.id for q in coding_questions], min(len(coding_questions), CODING_LIMIT))

    t = Test(candidate_id=c.id, question_ids=chosen_mcqs + chosen_coding, start_time=datetime.utcnow())
    db.add(t)
    db.commit()
    db.refresh(t)

    mcqs = []
    for qid in chosen_mcqs:
        q = db.get(Question, qid)
        mcqs.append({"id": q.id, "question": q.question_text, "options": q.options, "type": "mcq"})

    coding = []
    for qid in chosen_coding:
        q = db.get(Question, qid)
        coding.append({"id": q.id, "question": q.question_text, "test_cases": q.test_cases, "type": "coding"})

    return {"mcqs": mcqs, "coding": coding, "test_id": t.id}

@app.post("/run-code")
async def run_code(language: str = Body(...), code: str = Body(...), test_input: str = Body(""), db: Session = Depends(get_db)):
    try:
        result = await code_executor.execute_code(language, code, test_input, timeout=30)
        return {
            "status": "success" if result.status != "Time Limit Exceeded" else "timeout",
            "output": result.stdout or "",
            "error": result.stderr or "",
            "execution_status": result.status
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/submit-answers")
def submit_answers(payload: SubmitPayload, db: Session = Depends(get_db)):
    t = db.get(Test, payload.test_id)
    if not t: raise HTTPException(status_code=400, detail="Invalid test")

    score_mcq = 0
    for ans in payload.answers:
        q = db.get(Question, int(ans.question_id))
        if not q: continue
        
        is_correct = None
        if q.qtype == "mcq":
            try:
                # Compare integer response with integer correct_answer
                is_correct = (int(ans.response) == int(q.correct_answer))
                if is_correct: score_mcq += 1
            except: pass
            
        db.add(Answer(test_id=t.id, question_id=q.id, response=str(ans.response), is_correct=is_correct))

    t.end_time = datetime.utcnow()
    t.score_mcq = score_mcq
    t.total_score = score_mcq 
    
    c = db.get(Candidate, t.candidate_id)
    c.has_taken_test = True
    db.commit()

    return {"score_mcq": t.score_mcq, "total_score": t.total_score}

@app.get("/admin/results")
def admin_results(db: Session = Depends(get_db)):
    tests = db.execute(select(Test).order_by(Test.id.desc())).scalars().all()
    out = []
    for t in tests:
        cand = db.get(Candidate, t.candidate_id)
        if not cand: continue

        answers = db.execute(select(Answer).where(Answer.test_id == t.id)).scalars().all()
        correct = len([a for a in answers if a.is_correct])
        
        out.append({
            "candidate": cand.name,
            "email": cand.email,
            "role": cand.role,
            "score_mcq": t.score_mcq,
            "score_coding": t.score_coding,
            "total_score": t.total_score,
            "accuracy_percentage": round((correct / len(answers) * 100), 1) if answers else 0,
            "start_time": t.start_time
        })
    return {"results": out}

@app.get("/admin/question-count")
def question_count(db: Session = Depends(get_db)):
    mcq = db.query(Question).filter(Question.qtype == "mcq").count()
    coding = db.query(Question).filter(Question.qtype == "coding").count()
    roles = db.query(Question.role, func.count(Question.id)).group_by(Question.role).all()
    
    return {
        "total": mcq + coding,
        "by_type": {"mcqs": mcq, "coding": coding},
        "by_role": {r[0]: r[1] for r in roles}
    }

@app.get("/admin/question-preview/{role}")
def preview_questions(role: str, db: Session = Depends(get_db)):
    mcqs = db.execute(select(Question).where(Question.qtype=="mcq", Question.role==role)).scalars().all()
    coding = db.execute(select(Question).where(Question.qtype=="coding", Question.role==role)).scalars().all()
    
    return {
        "mcq_sample": [{"question": q.question_text, "options": q.options, "correct_answer": q.correct_answer} for q in mcqs],
        "coding_sample": [{"question": q.question_text, "test_cases": q.test_cases} for q in coding]
    }

@app.get("/admin/logs")
def get_generation_logs():
    log_file = Path(__file__).parent / "llm_generation.log"
    if not log_file.exists(): return {"status": "no_logs"}
    with open(log_file, 'r', encoding='utf-8') as f:
        return {"logs": f.read()}

@app.delete("/admin/reset")
def reset_all(db: Session = Depends(get_db)):
    db.query(Answer).delete()
    db.query(Test).delete()
    db.query(Question).delete()
    db.query(Candidate).delete()
    db.commit()
    return {"status": "All data reset"}