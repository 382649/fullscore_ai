"""
app.py - Study Helper web app (Streamlit).
Run on your computer:  python -m streamlit run app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

from file_reader import FileReadError, read_uploaded_files
from study_engine import StudyEngine, StudyError

load_dotenv()

st.set_page_config(page_title="Study Helper", page_icon="📚", layout="wide")


def get_api_key():
    """Online: from Streamlit Secrets. On your computer: from the .env file."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY")


# ---------- memory of the page ----------
for key, default in {
    "text": "", "file_names": "", "summary": "", "quiz": None,
    "submitted": False, "answers": {}, "qa": [],
}.items():
    st.session_state.setdefault(key, default)

# ---------- sidebar ----------
with st.sidebar:
    st.header("📚 Study Helper")
    st.write("Gemini key:", "✅" if get_api_key() else "❌ missing")
    st.divider()
    st.caption("1. Upload your notes\n\n2. Choose Summary or Quiz\n\n3. Study and test yourself")

st.title("📚 Study Helper")
st.caption("Upload your study material and get a summary or a quiz.")

# ---------- upload ----------
files = st.file_uploader(
    "Upload PDF, TXT or MD files", type=["pdf", "txt", "md"], accept_multiple_files=True
)
pasted = st.text_area("...or paste your notes here", height=120)

if st.button("📥 Load material", type="primary"):
    try:
        parts = []
        if files:
            parts.append(read_uploaded_files(files))
        if pasted.strip():
            parts.append(pasted.strip())
        if not parts:
            st.warning("Please upload a file or paste some text first.")
        else:
            text = "\n\n".join(parts)
            if len(text) < 100:
                raise FileReadError("The text is too short. Please add more material.")
            st.session_state.text = text
            st.session_state.file_names = ", ".join(f.name for f in files) if files else "Pasted text"
            st.session_state.summary = ""
            st.session_state.quiz = None
            st.session_state.submitted = False
            st.session_state.answers = {}
            st.session_state.qa = []
    except FileReadError as e:
        st.error(str(e))

if not st.session_state.text:
    st.info("Load some study material to begin.")
    st.stop()

text = st.session_state.text
st.success(f"Material loaded: {st.session_state.file_names}  ({len(text.split()):,} words)")

try:
    engine = StudyEngine(get_api_key(), os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
except StudyError as e:
    st.error(str(e))
    st.stop()

tab_sum, tab_quiz, tab_ask = st.tabs(["📝 Summary", "❓ Quiz", "💬 Ask a question"])

# ---------- summary tab ----------
with tab_sum:
    style = st.selectbox("Summary type", ["Short summary", "Detailed summary", "Key points", "Exam notes"])
    if st.button("Make summary"):
        bar = st.progress(0.0)
        try:
            st.session_state.summary = engine.summarize(
                text, style, progress=lambda m, f: (bar.progress(min(f, 1.0)), st.caption(m))
            )
        except StudyError as e:
            st.error(str(e))
        bar.empty()

    if st.session_state.summary:
        st.markdown(st.session_state.summary)
        st.download_button("⬇️ Download summary", st.session_state.summary,
                           file_name="summary.txt", mime="text/plain")

# ---------- quiz tab ----------
with tab_quiz:
    c1, c2 = st.columns(2)
    num = c1.slider("Number of questions", 3, 15, 5)
    level = c2.select_slider("Difficulty", ["Easy", "Medium", "Hard"], value="Medium")

    if st.button("Make quiz"):
        try:
            with st.spinner("Creating your quiz..."):
                st.session_state.quiz = engine.make_quiz(text, num, level)
            st.session_state.submitted = False
            st.session_state.answers = {}
        except StudyError as e:
            st.error(str(e))

    quiz = st.session_state.quiz
    if quiz:
        letters = "ABCD"
        if not st.session_state.submitted:
            with st.form("quiz_form"):
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i + 1}. {q['question']}**")
                    st.radio("Choose one", range(4), index=None, key=f"q{i}",
                             format_func=lambda n, opts=q["options"]: f"{letters[n]}. {opts[n]}",
                             label_visibility="collapsed")
                    st.write("")
                if st.form_submit_button("✅ Submit answers"):
                    st.session_state.answers = {i: st.session_state.get(f"q{i}") for i in range(len(quiz))}
                    st.session_state.submitted = True
                    st.rerun()
        else:
            answers = st.session_state.answers
            score = sum(1 for i, q in enumerate(quiz) if answers.get(i) == q["answer_index"])
            st.subheader(f"Your score: {score} / {len(quiz)}")
            st.progress(score / len(quiz))
            for i, q in enumerate(quiz):
                mine, right = answers.get(i), q["answer_index"]
                st.markdown(f"**Q{i + 1}. {q['question']}**")
                if mine == right:
                    st.success(f"Correct: {letters[right]}. {q['options'][right]}")
                else:
                    your = f"{letters[mine]}. {q['options'][mine]}" if mine is not None else "No answer"
                    st.error(f"Your answer: {your}")
                    st.info(f"Correct answer: {letters[right]}. {q['options'][right]}")
                if q["explanation"]:
                    st.caption(q["explanation"])
            if st.button("🔄 Try again"):
                st.session_state.submitted = False
                for i in range(len(quiz)):
                    st.session_state.pop(f"q{i}", None)
                st.rerun()

        # download the quiz with answers
        lines = []
        for i, q in enumerate(quiz, 1):
            lines.append(f"Q{i}. {q['question']}")
            lines += [f"   {letters[n]}. {o}" for n, o in enumerate(q["options"])]
            lines.append(f"   Answer: {letters[q['answer_index']]}  - {q['explanation']}\n")
        st.download_button("⬇️ Download quiz", "\n".join(lines), file_name="quiz.txt", mime="text/plain")

# ---------- ask tab ----------
with tab_ask:
    st.caption("Answers come only from your study material.")
    for q, a in st.session_state.qa:
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.markdown(a)
    question = st.chat_input("Ask something about your material...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking..."):
                    reply = engine.answer(question, text)
                st.markdown(reply)
                st.session_state.qa.append((question, reply))
            except StudyError as e:
                st.error(str(e))
