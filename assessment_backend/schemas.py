from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Union

# --- External API Structures ---
class ExternalRole(BaseModel):
    roleId: int
    role_name: Optional[str] = None

class ExternalCandidate(BaseModel):
    candidateId: int
    name: str
    cEmail: str
    candidateRole: ExternalRole

# --- Internal Structures ---
class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    role : str
    external_id: Optional[int] = None

class CandidateAuth(BaseModel):
    email: EmailStr

class MCQ(BaseModel):
    id: int
    question: str
    options: list

class Coding(BaseModel):
    id: int
    question: str
    test_cases: list

class StartTestResponse(BaseModel):
    mcqs: list
    coding: list
    test_id: int

class SubmitAnswer(BaseModel):
    question_id: Union[int, str]
    response: Any

class SubmitPayload(BaseModel):
    email: EmailStr
    test_id: int
    answers: List[SubmitAnswer]