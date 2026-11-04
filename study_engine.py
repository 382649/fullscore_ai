"""
study_engine.py - The AI part. Uses Gemini to:
  - make a summary
  - make a quiz
  - answer questions about the material

Rule for the AI: use ONLY the uploaded material. Do not make things up.
"""

import json
import re
import time

from google import genai
from google.genai import types

MODEL_DEFAULT = "gemini-2.5-flash"
CHUNK_SIZE = 12000      # letters per piece when the material is long
MAX_CHUNKS = 8          # stop after this many pieces to save time and quota
QUIZ_TEXT_LIMIT = 30000  # how much text we send for the quiz


class StudyError(Exception):
    """A friendly message that can be shown to the user."""


def _parse_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def split_chunks(text, size=CHUNK_SIZE):
    """Cut long text into pieces, ending each piece at a paragraph break if possible."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind("\n", start, end)
            if cut > start + size // 2:
                end = cut
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


class StudyEngine:
    def __init__(self, api_key, model=MODEL_DEFAULT):
        if not api_key:
            raise StudyError("Gemini API key is missing. Add GEMINI_API_KEY in Secrets (online) or the .env file (on your computer).")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    # ---------- talk to Gemini ----------
    def _call(self, prompt, json_mode=False, retries=3):
        config = types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        last = None
        for attempt in range(retries):
            try:
                resp = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                if not resp.text:
                    raise StudyError("Gemini returned an empty answer.")
                return resp.text
            except Exception as e:
                last = e
                msg = str(e).lower()
                if "api key" in msg or "401" in msg or "403" in msg or "permission" in msg:
                    raise StudyError(f"Gemini rejected the API key: {e}")
                time.sleep(2 * (attempt + 1))
        raise StudyError(f"Gemini failed after {retries} tries: {last}")

    # ---------- summary ----------
    def summarize(self, text, style="Short summary", progress=None):
        styles = {
            "Short summary": "a short summary of about 150 words, in 1-2 paragraphs",
            "Detailed summary": "a detailed summary with headings for each main topic, in simple words",
            "Key points": "a bullet list of the 10-15 most important points to remember",
            "Exam notes": "revision notes: headings, bullet points, important terms in bold, and formulas or dates if present",
        }
        goal = styles.get(style, styles["Short summary"])

        chunks = split_chunks(text)[:MAX_CHUNKS]
        notes = []
        if len(chunks) > 1:
            # Long material: first make notes for each piece, then combine.
            for i, chunk in enumerate(chunks, 1):
                if progress:
                    progress(f"Reading part {i} of {len(chunks)}...", i / (len(chunks) + 1))
                notes.append(self._call(
                    "Write clear study notes for this part of a document. "
                    "Use only the text. Keep names, numbers, definitions.\n\n" + chunk
                ))
            material = "\n\n".join(notes)
        else:
            material = chunks[0]

        if progress:
            progress("Writing the final summary...", 0.95)
        return self._call(
            f"You are a study helper. Write {goal} from the study material below.\n"
            "Rules: use ONLY the material, do not add outside facts, use simple words, "
            "format with Markdown.\n\nSTUDY MATERIAL:\n" + material
        )

    # ---------- quiz ----------
    def make_quiz(self, text, num_questions=5, difficulty="Medium"):
        material = text[:QUIZ_TEXT_LIMIT]
        prompt = f"""You are a teacher. Make {num_questions} multiple choice questions
from the study material below. Difficulty: {difficulty}.

Rules:
- Use ONLY the material. Do not use outside knowledge.
- Each question has exactly 4 options and exactly 1 correct answer.
- Make wrong options believable, not silly.
- Cover different parts of the material.
- Give a short explanation of why the answer is correct.

Return ONLY JSON in this form:
[{{"question": "...", "options": ["A text", "B text", "C text", "D text"],
   "answer_index": 0, "explanation": "..."}}]
(answer_index is 0 for the first option, 1 for the second, and so on.)

STUDY MATERIAL:
{material}"""
        data = None
        for _ in range(2):
            try:
                data = _parse_json(self._call(prompt, json_mode=True))
                break
            except StudyError:
                raise
            except Exception:
                continue
        if not isinstance(data, list):
            raise StudyError("Could not build the quiz. Please try again.")

        quiz = []
        for q in data:
            try:
                options = [str(o) for o in q["options"]]
                idx = int(q["answer_index"])
                if len(options) == 4 and 0 <= idx < 4 and str(q["question"]).strip():
                    quiz.append({
                        "question": str(q["question"]).strip(),
                        "options": options,
                        "answer_index": idx,
                        "explanation": str(q.get("explanation", "")).strip(),
                    })
            except (KeyError, TypeError, ValueError):
                continue
        if not quiz:
            raise StudyError("The quiz came out in the wrong format. Please try again.")
        return quiz

    # ---------- ask a question ----------
    def answer(self, question, text):
        return self._call(
            "Answer the student's question using ONLY the study material below. "
            "Use simple words. If the answer is not in the material, say: "
            "'This is not in your study material.'\n\n"
            f"QUESTION: {question}\n\nSTUDY MATERIAL:\n{text[:QUIZ_TEXT_LIMIT]}"
        )
