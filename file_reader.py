"""
file_reader.py - Reads text out of the files the student uploads (PDF, TXT, MD).
"""

import io

from pypdf import PdfReader


class FileReadError(Exception):
    """A friendly message that can be shown to the user."""


def read_pdf(data):
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise FileReadError("This PDF is password protected. Please remove the password and try again.")
        pages = [(page.extract_text() or "") for page in reader.pages]
    except FileReadError:
        raise
    except Exception as e:
        raise FileReadError(f"Could not read this PDF: {e}")
    return "\n".join(pages)


def read_text(data):
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise FileReadError("Could not read this text file.")


def read_uploaded_files(files):
    """
    files = list of Streamlit uploaded files.
    Returns all the text joined together.
    """
    parts = []
    for f in files:
        name = f.name.lower()
        data = f.getvalue()
        if name.endswith(".pdf"):
            text = read_pdf(data)
        elif name.endswith((".txt", ".md")):
            text = read_text(data)
        else:
            raise FileReadError(f"'{f.name}' is not supported. Upload PDF, TXT or MD files.")
        if text.strip():
            parts.append(text)

    full = "\n\n".join(parts).strip()
    if len(full) < 100:
        raise FileReadError(
            "Not enough text found. If your PDF is a scanned image, it has no real text. "
            "Try a PDF where you can select the words, or paste the text in a TXT file."
        )
    return full
