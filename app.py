# app.py - robust, import-safe Resume Screener for Streamlit Cloud
# Copy/replace this file in your repo and deploy. It won't crash on missing modules.

import streamlit as st
from io import BytesIO
from datetime import datetime
import re

# Try optional imports (fail gracefully)
_pdf_readers = {}

# 1) Try PyPDF2
try:
    from PyPDF2 import PdfReader as PyPDF2_Reader
    _pdf_readers['PyPDF2'] = True
except Exception:
    _pdf_readers['PyPDF2'] = False

# 2) Try pypdf
try:
    from pypdf import PdfReader as Pypdf_Reader
    _pdf_readers['pypdf'] = True
except Exception:
    _pdf_readers['pypdf'] = False

# 3) Try PyMuPDF (fitz)
try:
    import fitz
    _pdf_readers['fitz'] = True
except Exception:
    _pdf_readers['fitz'] = False

# 4) Try pdfplumber
try:
    import pdfplumber
    _pdf_readers['pdfplumber'] = True
except Exception:
    _pdf_readers['pdfplumber'] = False

# DOCX support
try:
    import docx
    _docx_available = True
except Exception:
    _docx_available = False

# PDF writer
try:
    from fpdf import FPDF
    _fpdf_available = True
except Exception:
    _fpdf_available = False


def _safe_text(obj):
    return obj or ""


def sanitize_for_fpdf(s: str) -> str:
    if not s:
        return ""
    return (s.replace("—", "-")
            .replace("–", "-")
            .replace("•", "-")
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("\u2013", "-")
            .replace("\u2022", "-"))


def extract_text_pdf_bytes(file_like) -> str:
    try:
        file_like.seek(0)
    except Exception:
        pass

    text = ""

    # PyPDF2
    if _pdf_readers.get('PyPDF2'):
        try:
            file_like.seek(0)
            reader = PyPDF2_Reader(file_like)
            for p in reader.pages:
                page_text = p.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception:
            pass

    # pypdf
    if _pdf_readers.get('pypdf'):
        try:
            file_like.seek(0)
            reader = Pypdf_Reader(file_like)
            for p in reader.pages:
                page_text = p.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception:
            pass

    # fitz
    if _pdf_readers.get('fitz'):
        try:
            file_like.seek(0)
            doc = fitz.open(stream=file_like.read(), filetype="pdf")
            for p in doc:
                page_text = p.get_text("text")
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception:
            pass

    # pdfplumber
    if _pdf_readers.get('pdfplumber'):
        try:
            file_like.seek(0)
            with pdfplumber.open(file_like) as pdf:
                for p in pdf.pages:
                    page_text = p.extract_text() or ""
                    text += page_text + "\n"
            return text
        except Exception:
            pass

    return ""


def extract_text_docx_bytes(file_like) -> str:
    try:
        file_like.seek(0)
        d = docx.Document(file_like)
        return "\n".join(p.text for p in d.paragraphs if p.text)
    except Exception:
        return ""


def extract_text_txt_bytes(file_like) -> str:
    try:
        file_like.seek(0)
        raw = file_like.read()
        if isinstance(raw, bytes):
            try:
                return raw.decode("utf-8", errors="replace")
            except Exception:
                return raw.decode("latin-1", errors="replace")
        return str(raw)
    except Exception:
        return ""


REQUIRED_SKILLS = [
    "typing", "data entry", "ms word", "excel", "internet browsing",
    "detail oriented", "organized", "communication", "time management"
]


def clean_and_normalize(s: str) -> str:
    s = _safe_text(s)
    s = s.replace('\r', ' ').replace('\t', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()


def get_found_missing(text: str):
    text = clean_and_normalize(text)
    found, missing = [], []
    for skill in REQUIRED_SKILLS:
        if skill in text:
            found.append(skill)
        else:
            missing.append(skill)
    match_pct = int((len(found) / len(REQUIRED_SKILLS)) * 100)
    return found, missing, match_pct


def make_pdf_bytes(name, match_pct, found, missing, summary, recs):
    summary = sanitize_for_fpdf(summary)
    recs = sanitize_for_fpdf(recs)

    if _fpdf_available:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(0, 8, "Resume Screening Report", ln=True)
        pdf.cell(0, 8, f"Candidate: {name}", ln=True)
        pdf.cell(0, 8, f"Match Score: {match_pct}%", ln=True)
        pdf.ln(5)

        pdf.cell(0, 7, "Found Skills:", ln=True)
        for s in found or ["None"]:
            pdf.cell(0, 6, f"- {s}", ln=True)

        pdf.ln(3)
        pdf.cell(0, 7, "Missing Skills:", ln=True)
        for s in missing or ["None"]:
            pdf.cell(0, 6, f"- {s}", ln=True)

        pdf.ln(3)
        pdf.multi_cell(0, 6, "Summary:\n" + summary)
        pdf.ln(2)
        pdf.multi_cell(0, 6, "Recommendations:\n" + recs)

        out = pdf.output(dest="S")
        if isinstance(out, str):
            out = out.encode("latin-1", errors="replace")
        return out

    txt = "\n".join([
        "Resume Screening Report",
        f"Candidate: {name}",
        f"Match Score: {match_pct}%",
        "",
        "Found Skills:",
        *[f"- {s}" for s in found or ["None"]],
        "",
        "Missing Skills:",
        *[f"- {s}" for s in missing or ["None"]],
        "",
        "Summary:",
        summary,
        "",
        "Recommendations:",
        recs
    ])
    return txt.encode("utf-8")


# ---------- UI ----------
st.set_page_config(page_title="Resume Screener", layout="wide")
st.title("Resume Screener - Where resumes meet precision.")
st.write("AI-powered resume screening for faster, smarter hiring.")

st.sidebar.header("JOB DESCRIPTION")
sample_jd = """We are seeking a Data Entry Operator with strong typing skills and attention to detail. Responsibilities include typing and entering data, maintaining records in MS Word and Excel, internet research. Typing speed above 35 WPM."""
jd = st.sidebar.text_area("Paste your job description here", value=sample_jd, height=200)

st.sidebar.markdown("**Upload** a single resume (PDF/DOCX/TXT) or paste the resume text below if extraction fails.")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded = st.file_uploader("Upload resume (pdf / docx / txt)", type=["pdf", "docx", "txt"])
    manual_text = st.text_area("OR paste resume text here (plain text)", height=250)

# Remove "Required skills checked..." text completely

resume_text = ""
extraction_warnings = []

if uploaded:
    ext = uploaded.name.split(".")[-1].lower()

    if ext == "pdf":
        try:
            resume_text = extract_text_pdf_bytes(uploaded)
            if not resume_text.strip():
                extraction_warnings.append("PDF extraction returned empty text.")
        except Exception as e:
            extraction_warnings.append(str(e))

    elif ext == "docx":
        if _docx_available:
            try:
                resume_text = extract_text_docx_bytes(uploaded)
            except Exception as e:
                extraction_warnings.append(str(e))
        else:
            extraction_warnings.append("DOCX support not available.")

    elif ext == "txt":
        try:
            resume_text = extract_text_txt_bytes(uploaded)
        except Exception as e:
            extraction_warnings.append(str(e))

if manual_text.strip():
    resume_text = manual_text

if not resume_text:
    st.warning("No resume text available yet. Upload or paste the resume text.")
else:
    found, missing, match_pct = get_found_missing(resume_text)

    st.subheader("Screening Result")
    st.metric("Match Score", f"{match_pct}%")
    st.write("**Skills found:**", ", ".join(found) if found else "None")
    st.write("**Missing skills:**", ", ".join(missing) if missing else "None")

    summary = f"Candidate matched {match_pct}% of required skills."
    recs = "Improve typing speed, MS Word, Excel, and time management."

    candidate_name = uploaded.name if uploaded else "pasted_resume"
    report_bytes = make_pdf_bytes(candidate_name, match_pct, found, missing, summary, recs)

    if _fpdf_available:
        fname = f"screening_report_{datetime.utcnow().strftime('%Y%m%d%H%M')}.pdf"
        st.download_button("Download PDF Report", data=report_bytes, file_name=fname, mime="application/pdf")
    else:
        fname = f"screening_report_{datetime.utcnow().strftime('%Y%m%d%H%M')}.txt"
        st.download_button("Download Report (TXT)", data=report_bytes, file_name=fname, mime="text/plain")

