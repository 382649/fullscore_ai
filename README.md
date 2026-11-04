# Study Helper

Upload your study material (PDF, TXT, MD) or paste notes. Get a summary, a quiz, or ask questions.

## Files
| File | Purpose |
|------|---------|
| `app.py` | The Streamlit screen (upload, Summary, Quiz, Ask tabs) |
| `file_reader.py` | Reads text from PDF and text files |
| `study_engine.py` | Gemini AI: summary, quiz, answers (only from your material) |
| `requirements.txt` | Packages to install |

## Run on your computer
```
python -m pip install -r requirements.txt
```
Create a `.env` file:
```
GEMINI_API_KEY=your_key_here
```
Start:
```
python -m streamlit run app.py
```
Get a free key at https://aistudio.google.com/apikey

## Put it online (GitHub + Streamlit)
1. Upload `app.py`, `file_reader.py`, `study_engine.py`, `requirements.txt` and `README.md` to a GitHub repository. Do NOT upload `.env`.
2. Go to https://share.streamlit.io, click **Create app**, pick the repository, main file `app.py`.
3. In **Advanced settings > Secrets**, paste:
   ```
   GEMINI_API_KEY = "your_key_here"
   ```
4. Click **Deploy**.

## Notes
- Scanned PDFs (photos of pages) have no real text, so they will not work. Use a PDF where you can select the words.
- Very long books: the summary reads up to about 8 parts, and the quiz and questions use the first part of the material (about 30,000 letters).
- Free Gemini keys have limits. If you see a rate limit message, wait a minute.
