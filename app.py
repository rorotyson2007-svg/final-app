# app.py - robust, import-safe Resume Screener for Streamlit Cloud
# Copy/replace this file in your repo and deploy. It won't crash on missing modules.

import streamlit as st
from io import BytesIO
from datetime import datetime
import re

# Try optional imports (fail gracefully)
_pdf_readers = {}

# 1) Try PyPDF2 (older name)
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

# Document reader for .docx
try:
    import docx
    _docx_available = True
except Exception:
    _docx_available = False

# PDF writer (report) - fpdf is usually available; handle if not
try:
    from fpdf import FPDF
    _fpdf_available = True
except Exception:
    _fpdf_available = False

# Utilities
def _safe_text(obj):
    """Ensure we return a str; None -> ''"""
    return obj or ""

def sanitize_for_fpdf(s: str) -> str:
    """Replace known problematic unicode characters for old FPDF fonts."""
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

# PDF extraction functions: try available libs in order
def extract_text_pdf_bytes(file_like) -> str:
    """Attempt to extract text from PDF bytes using any available reader."""
    # Ensure we can read multiple times
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

    # fitz / PyMuPDF
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

    # If we reach here, no PDF extraction lib worked
    return ""

# DOCX extraction
def extract_text_docx_bytes(file_like) -> str:
    try:
        file_like.seek(0)
        doc = docx.Document(file_like)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)
    except Exception:
        return ""

# TXT extraction
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

# Resume processing (simple, robust)
REQUIRED_SKILLS = [
    "typing", "data entry", "ms word", "excel", "internet browsing",
    "detail oriented", "organized", "communication", "time management"
]

def clean_and_normalize(s: str) -> str:
    s = _safe_text(s)
    s = s.replace('\r', ' ').replace('\t', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()

def get_found_missing(resume_text: str):
    resume_text = clean_and_normalize(resume_text)
    found = []
    missing = []
    for skill in REQUIRED_SKILLS:
        if skill in resume_text:
            found.append(skill)
        else:
            missing.append(skill)
    match_pct = int((len(found) / len(REQUIRED_SKILLS)) * 100)
    return found, missing, match_pct

# PDF report generation with safe fallback
def make_pdf_bytes(candidate_name: str, match_pct: float, found, missing, summary, recommendations):
    # sanitize strings for FPDF if used
    summary = sanitize_for_fpdf(summary)
    recommendations = sanitize_for_fpdf(recommendations)

    if _fpdf_available:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(0, 8, "Resume Screening Report", ln=True)
        pdf.cell(0, 7, f"Candidate: {candidate_name}", ln=True)
        pdf.cell(0, 7, f"Match Score: {match_pct:.1f}%", ln=True)
        pdf.ln(4)

        pdf.cell(0, 7, "Found Skills:", ln=True)
        if found:
            for s in found:
                pdf.cell(0, 6, f"- {sanitize_for_fpdf(s)}", ln=True)
        else:
            pdf.cell(0, 6, "- None detected", ln=True)

        pdf.ln(3)
        pdf.cell(0, 7, "Missing Skills:", ln=True)
        if missing:
            for s in missing:
                pdf.cell(0, 6, f"- {sanitize_for_fpdf(s)}", ln=True)
        else:
            pdf.cell(0, 6, "- None", ln=True)

        pdf.ln(4)
        pdf.multi_cell(0, 6, "Summary:\n" + summary)
        pdf.ln(2)
        pdf.multi_cell(0, 6, "Recommendations:\n" + recommendations)

        out = pdf.output(dest="S")
        if isinstance(out, str):
            out = out.encode("latin-1", errors="replace")
        return out

    # If FPDF not available, return a text file bytes
    txt = []
    txt.append("Resume Screening Report")
    txt.append(f"Candidate: {candidate_name}")
    txt.append(f"Match Score: {match_pct:.1f}%")
    txt.append("")
    txt.append("Found Skills:")
    txt.extend([f"- {s}" for s in found] or ["- None"])
    txt.append("")
    txt.append("Missing Skills:")
    txt.extend([f"- {s}" for s in missing] or ["- None"])
    txt.append("")
    txt.append("Summary:")
    txt.append(summary)
    txt.append("")
    txt.append("Recommendations:")
    txt.append(recommendations)

    out_txt = "\n".join(txt)
    return out_txt.encode("utf-8")

# ------------------ Streamlit UI ------------------

st.set_page_config(page_title="Resume Screener", layout="wide")
st.title("Resume Screener — From resume to results , instantly.)")

st.write("AI-powered resume screening for faster, smarter hiring.")


st.sidebar.header("Job Description")
jd = st.sidebar.text_area("Paste your job description here.", value=sample_jd, height=200)

st.sidebar.markdown("**Upload** a single resume (PDF/DOCX/TXT)")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded = st.file_uploader("Upload resume (pdf / docx / txt)", type=["pdf", "docx", "txt"])
    manual_text = st.text_area("OR paste resume text here (plain text)", height=250)

# Decide how to obtain resume_text
resume_text = ""
extraction_warnings = []

if uploaded:
    ext = uploaded.name.split(".")[-1].lower()
    # Try to extract depending on file type
    if ext == "pdf":
        try:
            resume_text = extract_text_pdf_bytes(uploaded)
            if not resume_text.strip():
                extraction_warnings.append("PDF extraction returned empty text — it might be a scanned image PDF.")
        except Exception as e:
            extraction_warnings.append(f"PDF extraction failed: {e}")
    elif ext == "docx":
        if _docx_available:
            try:
                resume_text = extract_text_docx_bytes(uploaded)
                if not resume_text.strip():
                    extraction_warnings.append("DOCX extraction returned empty text.")
            except Exception as e:
                extraction_warnings.append(f"DOCX extraction failed: {e}")
        else:
            extraction_warnings.append("DOCX support not available on this deployment.")
    elif ext == "txt":
        try:
            resume_text = extract_text_txt_bytes(uploaded)
        except Exception as e:
            extraction_warnings.append(f"TXT read failed: {e}")
    else:
        extraction_warnings.append("Unsupported upload type.")

# If user pasted text, prefer that
if manual_text and manual_text.strip():
    resume_text = manual_text

if not resume_text:
    st.warning("No resume text available yet. Upload a PDF/DOCX/TXT or paste the resume into the box on the left.")
    if extraction_warnings:
        st.info("Extraction info: " + " | ".join(extraction_warnings))
else:
    # Process resume_text
    found, missing, match_pct = get_found_missing(resume_text)
    st.subheader("Screening Result")
    st.metric("Match Score", f"{match_pct}%")
    st.write("**Skills found:**", ", ".join(found) if found else "None")
    st.write("**Missing skills:**", ", ".join(missing) if missing else "None")

    # Summaries & recs (simple)
    summary = f"Candidate matched {match_pct}% of the listed required skills."
    recs = "Recommendations: improve typing speed, MS Word and Excel proficiency, and time management."

    # Create report bytes
    candidate_name = uploaded.name if uploaded else "pasted_resume"
    report_bytes = make_pdf_bytes(candidate_name, match_pct, found, missing, summary, recs)

    # Download button with appropriate filename & mime
    # If we produced a PDF, mime 'application/pdf'; else provide text fallback
    if _fpdf_available:
        fname = f"screening_report_{candidate_name.rsplit('.',1)[0]}_{datetime.utcnow().strftime('%Y%m%d%H%M')}.pdf"
        st.download_button("Download PDF Report", data=report_bytes, file_name=fname, mime="application/pdf")
    else:
        fname = f"screening_report_{candidate_name.rsplit('.',1)[0]}_{datetime.utcnow().strftime('%Y%m%d%H%M')}.txt"
        st.download_button("Download Report (TXT)", data=report_bytes, file_name=fname, mime="text/plain")

    if extraction_warnings:
        st.info("Extraction notes: " + " | ".join(extraction_warnings))

st.markdown("---")
