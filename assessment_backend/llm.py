import os
import json
import httpx
import asyncio
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from dotenv import load_dotenv

# --- Logging Setup ---
def setup_file_logger():
    log_dir = Path(__file__).parent
    log_file = log_dir / "llm_generation.log"

    logger = logging.getLogger("llm_generator")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File Handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    file_handler.setFormatter(file_formatter)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_file_logger()

load_dotenv()

SERVER_URL = os.getenv("MISTRAL_API_URL")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL")
TIMEOUT = int(os.getenv("LLM_TIMEOUT", 360))

if SERVER_URL and SERVER_URL.endswith("/api/generate"):
    SERVER_URL = SERVER_URL.replace("/api/generate", "")

# --- Helper Functions ---

def estimate_tokens(text: str) -> int:
    """Rough estimation: 1 token ~= 4 chars"""
    if not text: return 0
    return len(text) // 4

def extract_json_block(text: str) -> Optional[str]:
    """Extract first valid JSON object or array."""
    if not text: return None
    # Remove markdown code blocks
    cleaned = text.replace("```json", "").replace("```", "").strip()
    # Regex to find the outer-most JSON object or list
    match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
    if match: return match.group(0)
    return cleaned

def safe_json_loads(content: str):
    """
    Safely load JSON with aggressive repairing for unescaped quotes.
    """
    if content is None: raise ValueError("No content")
    
    # 1. Try standard load first
    try:
        return json.loads(content)
    except:
        pass
    
    # 2. Extract JSON block if hidden in text
    extracted = extract_json_block(content)
    if not extracted:
        extracted = content

    try:
        return json.loads(extracted)
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON Decode Error: {e.msg} at line {e.lineno} col {e.colno}")
        logger.debug(f"⚠️ Context: {extracted[max(0, e.pos-20):min(len(extracted), e.pos+20)]}")

    # 3. Aggressive Repair (Common Mistral/Java issue: Unescaped quotes in keys/values)
    # This regex looks for double quotes that are NOT preceded by a backslash 
    # and are NOT structural JSON quotes (part of ": " or ", " or "}")
    # This is a heuristic and might not cover 100% of cases, but helps with code snippets.
    try:
        # Simple fix: Replace newlines with literal \n to prevent breaking single-line strings
        repaired = extracted.replace("\n", "\\n")
        return json.loads(repaired)
    except:
        pass

    logger.error("❌ Fatal: Could not parse JSON even after repair attempts.")
    return {"mcqs": [], "coding": []}

def load_reference_topics(role: str, question_type: str) -> str:
    normalized_role = role.lower()
    if "apex" in normalized_role: normalized_role = "apex"
    elif "react" in normalized_role: normalized_role = "react"
    elif "java" in normalized_role: normalized_role = "java"
    elif "oic" in normalized_role: normalized_role = "oic"
    
    filename = f"{normalized_role}_{question_type}_topics.txt"
    possible_paths = [
        Path(__file__).parent / "reference_topics" / filename,
        Path.cwd() / "reference_topics" / filename,
    ]
    for path in possible_paths:
        if path.exists():
            logger.info(f"✅ Found reference file: {path}")
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    
    logger.warning(f"⚠️ No topic file found for {filename}")
    return ""

def split_options_string(opt_str: str) -> List[str]:
    lines = [l.strip() for l in opt_str.splitlines() if l.strip()]
    if len(lines) >= 4: return lines
    parts = re.split(r'(?=\b[A-Da-d][\)\.]\s)', opt_str)
    return [p.strip() for p in parts if p.strip()][:4]

def normalize_option_text(opt: str) -> str:
    opt = opt.strip()
    opt = re.sub(r'^\s*[A-Da-d][\)\.\:]\s*', '', opt)
    return opt.strip()

def map_correct_to_index(correct, options: List[str]) -> int:
    try:
        idx = int(correct)
        if 0 <= idx < len(options): return idx
    except: pass
    
    s = str(correct).strip().upper()
    if len(s) == 1 and 'A' <= s <= 'D':
        return ord(s) - ord('A')
    
    match = re.search(r'^(OPTION|CHOICE)?\s*([A-D])', s)
    if match:
        char = match.group(2)
        return ord(char) - ord('A')

    s_norm = normalize_option_text(str(correct)).lower()
    for i, o in enumerate(options):
        if s_norm == normalize_option_text(o).lower():
            return i
            
    return 0

def normalize_mcq_entry(mcq: Dict[str, Any], role: str) -> Optional[Dict[str, Any]]:
    if not isinstance(mcq, dict) or not mcq.get("question"): return None
    
    opts = mcq.get("options", mcq.get("choices"))
    if isinstance(opts, str): opts = split_options_string(opts)
    if not opts or len(opts) < 4: return None
    
    opts = opts[:4]
    normalized_opts = [normalize_option_text(o) for o in opts]
    formatted_opts = [f"{label}) {text}" for label, text in zip(["A", "B", "C", "D"], normalized_opts)]
    
    correct_idx = map_correct_to_index(mcq.get("correct_answer"), normalized_opts)
    
    return {
        "question": mcq.get("question").strip(),
        "options": formatted_opts,
        "correct_answer": correct_idx,
        "difficulty": "hard",
        "role": role
    }

def normalize_coding_entry(code_q: Dict[str, Any], role: str) -> Optional[Dict[str, Any]]:
    if not isinstance(code_q, dict) or not code_q.get("question"): return None
    
    raw_cases = code_q.get("test_cases", code_q.get("examples", []))
    norm_cases = []
    for tc in raw_cases:
        if isinstance(tc, dict) and "input" in tc and "output" in tc:
            norm_cases.append({"input": str(tc["input"]), "output": str(tc["output"])})
            
    if not norm_cases: return None

    return {
        "question": code_q["question"].strip(),
        "difficulty": "hard",
        "role": role,
        "test_cases": norm_cases[:10],
        "options": code_q.get("options"),
        "correct_answer": code_q.get("correct_answer")
    }

# --- Prompts ---

def wrap_strict_json(prompt: str) -> str:
    return "CRITICAL: OUTPUT ONLY VALID JSON. NO MARKDOWN. NO EXPLANATION.\n" + prompt

def get_mcq_prompt(role: str, count: int, ref: str) -> str:
    ref_snippet = (ref or "General advanced concepts")[:2000]
    
    return (
        f"CONTEXT: You are a Senior {role} Interviewer.\n"
        f"SYLLABUS: Use the following topics:\n{ref_snippet}\n\n"
        f"TASK: Generate {count} HARD multiple-choice questions.\n"
        "RULES:\n"
        "1. Questions must be technical, scenario-based, or debugging focused.\n"
        "2. Provide exactly 4 options per question.\n"
        "3. **CRITICAL**: The 'correct_answer' must be the Integer index (0, 1, 2, or 3) of the correct option.\n"
        "4. Include a brief 'explanation' field to justify the answer.\n"
        "5. **ESCAPING RULES**: If the question contains code with double quotes (e.g. String s = \"Hi\"), you MUST escape them (e.g. String s = \\\"Hi\\\").\n"
        "6. Output VALID JSON format only.\n\n"
        'JSON STRUCTURE:\n'
        '{"mcqs": [\n'
        '  {\n'
        '    "question": "What is the output of...\\n```java\\nString s = \\"Hello\\";\\n```",\n'
        '    "options": ["A) Output X", "B) Error", "C) Output Y", "D) Null"],\n'
        '    "correct_answer": 2,\n'
        '    "explanation": "C is correct because..."\n'
        '  }\n'
        ']}'
    )

def get_coding_prompt(role: str, count: int, ref: str) -> str:
    ref_snippet = (ref or "General advanced algorithms")[:2000]
    return (
        f"CONTEXT: You are a Senior {role} Interviewer.\n"
        f"SYLLABUS: {ref_snippet}\n\n"
        f"TASK: Generate {count} HARD coding challenges.\n"
        "RULES:\n"
        "1. Problems must require algorithmic thinking or complex data manipulation.\n"
        "2. Provide 3-5 Test Cases (input/output) for validation.\n"
        "3. Output valid JSON.\n\n"
        'JSON EXAMPLE:\n'
        '{"coding": [{"question": "Write a function...", "test_cases": [{"input": "arg1", "output": "result"}]}]}'
    )

# --- Async LLM Logic ---

async def make_llm_request(client: httpx.AsyncClient, payload: dict, desc: str) -> str:
    input_chars = len(payload.get("prompt", ""))
    input_tokens = estimate_tokens(payload.get("prompt", ""))
    
    logger.info(f"📡 Request: {desc} | Input Size: {input_chars} chars (~{input_tokens} tokens)")
    
    for attempt in range(1, 3):
        try:
            resp = await client.post(f"{SERVER_URL}/api/generate", json=payload, timeout=TIMEOUT)
            if resp.status_code == 200:
                api_json = resp.json()
                result_text = api_json.get("response", str(api_json))
                
                output_chars = len(result_text)
                output_tokens = estimate_tokens(result_text)
                
                logger.info(f"✅ Received: {desc} | Output Size: {output_chars} chars (~{output_tokens} tokens)")
                return result_text
            else:
                logger.warning(f"⚠️ HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            logger.warning(f"⚠️ Attempt {attempt} failed: {e}")
            await asyncio.sleep(2)
    raise RuntimeError(f"Failed to generate {desc}")

async def generate_mcq_questions(role: str, mcq_count: int = 20):
    ref = load_reference_topics(role, "mcq")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
        # Request slightly more than needed to allow for bad formatting filtering
        payload = {
            "model": MISTRAL_MODEL,
            "prompt": wrap_strict_json(get_mcq_prompt(role, mcq_count + 3, ref)),
            "stream": False,
            "temperature": 0.3, # Lowered to 0.3 to reduce syntax errors
            "max_tokens": 4096,
        }
        
        try:
            raw_text = await make_llm_request(client, payload, f"Generate MCQs {role}")
            
            # --- DEBUG: Print specific part to verify 'explanation' exists ---
            snippet_end = min(len(raw_text), 600)
            logger.debug(f"🔍 RAW JSON SNAPSHOT (First 600 chars):\n{raw_text[:snippet_end]}\n...")
            # ---------------------------------------------------------------

            data = safe_json_loads(raw_text)
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return {"mcqs": []}

        raw_list = data.get("mcqs", []) if isinstance(data, dict) else []
        
        # Normalize
        final_list = []
        for item in raw_list:
            n = normalize_mcq_entry(item, role)
            if n: final_list.append(n)
            
        logger.info(f"✅ Processed {len(final_list)} valid MCQs out of {len(raw_list)} raw items")
        return {"mcqs": final_list[:mcq_count]}

async def generate_coding_questions(role: str, coding_count: int = 5):
    ref = load_reference_topics(role, "coding")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
        payload = {
            "model": MISTRAL_MODEL,
            "prompt": wrap_strict_json(get_coding_prompt(role, coding_count + 1, ref)),
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        
        try:
            raw_text = await make_llm_request(client, payload, f"Generate Coding {role}")
            data = safe_json_loads(raw_text)
        except Exception as e:
            logger.error(f"❌ Coding Generation failed: {e}")
            return {"coding": []}

        raw_list = data.get("coding", []) if isinstance(data, dict) else []
        
        final_list = []
        for item in raw_list:
            n = normalize_coding_entry(item, role)
            if n: final_list.append(n)
            
        logger.info(f"✅ Processed {len(final_list)} valid Coding questions")
        return {"coding": final_list[:coding_count]}

def run_sync(coro):
    return asyncio.get_event_loop().run_until_complete(coro)