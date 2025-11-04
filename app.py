import streamlit as st
import pdfplumber
import re
from fpdf import FPDF

st.set_page_config(page_title="Resume Screener", layout="wide")

# ---- Job Description ----
JOB_DESCRIPTION = """
We are seeking a Data Entry Operator with strong typing skills and attention to detail.

Responsibilities:
- Typing and entering data with accuracy and speed
- Maintaining records in MS Word and Excel
- Working independently and completing tasks on time
- Performing online research and internet data collection

Required Skills:
- Typing speed above 35 WPM
- Knowledge of MS Word, Excel, and Internet Browsing
- Detail-oriented and organized
- Good communication and time management

Freshers and students are welcome to apply.
"""

# ---- Skills List ----
REQUIRED_SKILLS = [
    "typing", "data entry", "ms word", "excel", "internet browsing",
    "detail oriented", "organized", "communication", "time management"
]

# ---- PDF Text Extractor (NO PyPDF2) ----
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text.lower()


# ---- Match Calculator ----
def match_skills(resume_text):
    found = []
    missing = []

    for skill in REQUIRED_SKILLS:
        if skill in resume_text:
            found.append(skill)
        else:
            missing.append(skill)

    match_pct = int((len(found) / len(REQUIRED_SKILLS)) * 100)
    return found, missing, match_pct


# ---- PDF Report (NO CUSTOM FONT) ----
def create_pdf_report(name, match, found, missing, summary, recs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, txt=f"Resume Screening Report - {name}", ln=1)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt=f"Match Percentage: {match}%", ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt="Skills Found:", ln=1)
    for s in found:
        pdf.cell(0, 8, f"- {s}", ln=1)

    pdf.ln(5)
    pdf.cell(0, 10, txt="Missing Skills:", ln=1)
    for s in missing:
        pdf.cell(0, 8, f"- {s}", ln=1)

    pdf.ln(5)
    pdf.multi_cell(0, 8, f"Summary:\n{summary}")

    pdf.ln(5)
    pdf.multi_cell(0, 8, f"Recommendations:\n{recs}")

    return pdf.output(dest="S").encode("latin-1")


# ---- UI ----
st.title("✅ Resume Screener (No Errors Version)")
st.write("Upload resume PDF and get instant screening result.")

uploaded = st.file_uploader("Upload Resume (PDF only)", type=["pdf"])

if uploaded:
    resume_text = extract_text_from_pdf(uploaded)

    found, missing, match = match_skills(resume_text)

    st.subheader("✅ Match Result")
    st.write(f"**Match: {match}%**")
    st.write(f"✅ Found: {', '.join(found)}")
    st.write(f"❌ Missing: {', '.join(missing)}")

    summary = f"The candidate matches {match}% of the required skills."
    recs = "Improve typing, MS Word, Excel, and organization skills to increase match score."

    report = create_pdf_report("Candidate", match, found, missing, summary, recs)

    st.download_button(
        "📥 Download PDF Report",
        data=report,
        file_name="resume_report.pdf",
        mime="application/pdf"
    )

