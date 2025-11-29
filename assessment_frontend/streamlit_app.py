import streamlit as st
import requests
import time
import logging
import pandas as pd
import html
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="Assessment Portal", page_icon="📝", layout="wide")

# ---------------------- Helper Functions ----------------------

def safe_text(text):
    """Sanitize text to prevent InvalidCharacterError in HTML rendering"""
    if not text: return ""
    return html.escape(str(text))

def display_generated_questions_pdf_style(mcqs, coding_questions, role):
    st.markdown("---")
    st.markdown(f"## 📋 Generated Questions for {role.upper()}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📝 Total MCQs", len(mcqs))
    col2.metric("💻 Coding Questions", len(coding_questions))
    col3.metric("📊 Total Questions", len(mcqs) + len(coding_questions))
    
    st.markdown("---")
    
    # MCQ Section
    if mcqs:
        st.markdown(f"### 📝 Multiple Choice Questions")
        for idx, mcq in enumerate(mcqs, 1):
            with st.container():
                # Escape the question text
                safe_q = safe_text(mcq.get('question', 'N/A'))
                
                st.markdown(f"""
                <div style='background-color: #262730; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #414141;'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span style='color: #4da6ff; font-weight: bold;'>Q{idx}</span>
                        <span style='background-color: #ff4b4b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;'>HARD</span>
                    </div>
                    <div style='color: #ffffff; margin-top: 10px; white-space: pre-wrap;'>{safe_q}</div>
                </div>
                """, unsafe_allow_html=True)
                
                options = mcq.get('options', [])
                correct = mcq.get('correct_answer', 0)
                
                for i, opt in enumerate(options):
                    safe_opt = safe_text(opt)
                    if i == correct:
                        st.success(f"✅ {safe_opt} (Correct)")
                    else:
                        st.text(f"⚪ {safe_opt}")
                st.markdown("---")
    
    # Coding Section
    if coding_questions:
        st.markdown(f"### 💻 Coding Questions")
        for idx, code_q in enumerate(coding_questions, 1):
            safe_q = safe_text(code_q.get('question', 'N/A'))
            st.markdown(f"""
            <div style='background-color: #1e2a1e; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #2e7d32;'>
                <div style='color: #81c784; font-weight: bold;'>Coding Q{idx}</div>
                <div style='color: #ffffff; margin-top: 10px; white-space: pre-wrap;'>{safe_q}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if code_q.get('test_cases'):
                with st.expander("Show Test Cases"):
                    for tc in code_q['test_cases']:
                        st.code(f"Input: {tc.get('input')}\nOutput: {tc.get('output')}")
            st.markdown("---")

def timer_component(total_minutes=60):
    start_ts = st.session_state.get("start_ts")
    if not start_ts: return
    
    elapsed = int(time.time()) - start_ts
    remaining = total_minutes * 60 - elapsed
    
    if remaining < 0:
        st.error("⏳ Time is up!")
        return
    
    mins, secs = divmod(remaining, 60)
    st.metric("⏳ Time Remaining", f"{mins:02d}:{secs:02d}")

# ---------------------- Pages ----------------------

def start_page():
    st.title("🎯 Candidate Test Portal")
    with st.form("start_test"):
        email = st.text_input("📧 Enter registered email")
        if st.form_submit_button("Start Test"):
            try:
                r = requests.post(f"{BACKEND}/start-test", json={"email": email}, timeout=15)
                if r.status_code == 200:
                    st.session_state.email = email
                    st.session_state.test = r.json()
                    st.session_state.answers = {}
                    st.session_state.start_ts = int(time.time())
                    st.session_state.page = "test"
                    st.session_state.current_q = 0
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Error"))
            except Exception as e:
                st.error(f"Connection failed: {e}")

def test_page():
    st.title("📝 Assessment")
    timer_component(60)
    
    test = st.session_state.get("test", {})
    all_qs = test.get("mcqs", []) + test.get("coding", [])
    
    if st.session_state.current_q >= len(all_qs):
        st.session_state.page = "submit"
        st.rerun()
        return

    q = all_qs[st.session_state.current_q]
    st.progress((st.session_state.current_q + 1) / len(all_qs))
    st.write(f"Question {st.session_state.current_q + 1} of {len(all_qs)}")
    
    st.markdown(f"### {q['question']}")
    
    if q['type'] == 'mcq':
        opts = q.get('options', [])
        choice = st.radio("Choose:", opts, key=f"q_{q['id']}")
        if st.button("Next ➡️"):
            idx = opts.index(choice) if choice in opts else 0
            st.session_state.answers[q['id']] = idx
            st.session_state.current_q += 1
            st.rerun()
            
    else:
        lang = st.selectbox("Language", ["python", "java"], key=f"lang_{q['id']}")
        code = st.text_area("Solution", height=200, key=f"code_{q['id']}")
        
        c1, c2 = st.columns(2)
        if c1.button("▶️ Run Code"):
            with st.spinner("Executing..."):
                try:
                    r = requests.post(f"{BACKEND}/run-code", json={"language": lang, "code": code}, timeout=35)
                    res = r.json()
                    if res['status'] == 'success':
                        st.success("Executed Successfully")
                        st.code(res['output'])
                    else:
                        st.error(f"Error: {res.get('error')}")
                except Exception as e:
                    st.error(str(e))
                    
        if c2.button("Next ➡️"):
            st.session_state.answers[q['id']] = {"code": code, "language": lang}
            st.session_state.current_q += 1
            st.rerun()

def submit_page():
    st.title("✅ Test Complete")
    if st.button("Submit Final Answers"):
        payload = {
            "email": st.session_state.email,
            "test_id": st.session_state.test['test_id'],
            "answers": [{"question_id": k, "response": v} for k, v in st.session_state.answers.items()]
        }
        try:
            r = requests.post(f"{BACKEND}/submit-answers", json=payload)
            if r.status_code == 200:
                st.success(f"Submitted! Score: {r.json().get('score_mcq')}")
                st.session_state.page = "done"
            else:
                st.error("Submission failed")
        except: st.error("Network error")

def admin_page():
    st.title("🔧 Admin Dashboard")
    tabs = st.tabs(["👥 Candidates", "⚙️ Generate", "📊 Results", "📜 Logs"])
    
    with tabs[0]: # Candidates Tab
        # Display Success Message if it exists in session state
        if "auth_success_msg" in st.session_state:
            st.success(st.session_state.auth_success_msg)
            # Remove it so it doesn't stay forever on next interactions
            del st.session_state.auth_success_msg

        if st.button("Sync External"):
            with st.spinner("Syncing..."):
                r = requests.get(f"{BACKEND}/admin/sync-external-candidates")
                if r.status_code == 200: st.success("Synced")
        
        cands = requests.get(f"{BACKEND}/admin/candidates").json()
        if cands:
            df = pd.DataFrame(cands)
            st.dataframe(df[['name', 'email', 'role', 'authorized', 'has_taken_test']])
            
            unauth = [c['email'] for c in cands if not c['authorized']]
            if unauth:
                e = st.selectbox("Authorize:", unauth)
                if st.button("Authorize Candidate"):
                    requests.post(f"{BACKEND}/admin/authorize", json={"email": e})
                    # Set message in session state so it survives the rerun
                    st.session_state.auth_success_msg = f"✅ Successfully authorized {e}"
                    st.rerun()

    with tabs[1]: # Generate Tab
        c1, c2 = st.columns(2)
        role = c1.selectbox("Role", ["apex", "react", "java", "oic"])
        qtype = c2.radio("Type", ["MCQ", "Coding"])
        
        if st.button("🚀 Generate & Verify"):
            with st.spinner(f"Generating {role} {qtype} (Process: Generate -> Verify)..."):
                ep = "/admin/generate-mcq" if qtype == "MCQ" else "/admin/generate-coding"
                try:
                    # Increased timeout for verification step
                    requests.post(f"{BACKEND}{ep}", json={"role": role}, timeout=300) 
                    st.success("Generation Complete!")
                    st.session_state.preview_trigger = True
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.button("Preview Questions") or st.session_state.get('preview_trigger'):
            data = requests.get(f"{BACKEND}/admin/question-preview/{role}").json()
            display_generated_questions_pdf_style(data['mcq_sample'], data['coding_sample'], role)
            st.session_state.preview_trigger = False

    with tabs[2]: # Results Tab
        if st.button("Refresh Results"):
            st.session_state.load_res = True
            
        if st.session_state.get('load_res'):
            r = requests.get(f"{BACKEND}/admin/results")
            if r.status_code == 200:
                res = r.json()['results']
                if res:
                    df = pd.DataFrame(res)
                    # Clean up columns for display
                    df = df[['candidate', 'role', 'score_mcq', 'score_coding', 'total_score', 'accuracy_percentage', 'start_time']]
                    df.columns = ['Name', 'Role', 'MCQ Score', 'Coding Score', 'Total', 'Accuracy %', 'Date']
                    
                    # FIX: Removed .background_gradient to fix ImportError
                    st.dataframe(
                        df.style.format({'Accuracy %': '{:.1f}%'}),
                        use_container_width=True
                    )
                else:
                    st.info("No results yet")

    with tabs[3]: # Logs Tab
        if st.button("Fetch Logs"):
            r = requests.get(f"{BACKEND}/admin/logs")
            st.text_area("Logs", r.json().get('logs', ''), height=400)
            
        if st.button("⚠️ RESET SYSTEM"):
            requests.delete(f"{BACKEND}/admin/reset")
            st.warning("System Reset")

def main():
    if "page" not in st.session_state: st.session_state.page = "start"
    
    sb = st.sidebar.radio("Navigation", ["Candidate Portal", "Admin Panel"])
    
    if sb == "Admin Panel":
        admin_page()
    else:
        if st.session_state.page == "start": start_page()
        elif st.session_state.page == "test": test_page()
        elif st.session_state.page == "submit": submit_page()
        else:
            st.title("Thank you!")
            st.info("Your test has been submitted.")

if __name__ == "__main__":
    main()