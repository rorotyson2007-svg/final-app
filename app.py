import streamlit as st
import fitz  # PyMuPDF
from fpdf import FPDF

st.set_page_config(page_title="Resume Screener", layout="wide")

JOB_DESCRIPTION = """
We are seeking a Data Entry Operator with strong typing skills and attention to detail.

Responsibilities:
- Typing and entering data with accuracy and speed
- Maintaining records in MS Word and Excel
- Working independently and completing tasks on time
- Performing online research and internet data collection

Skills required:
- Typing speed above 35 WPM
- Knowledge of MS Word, Excel, and Internet Browsing
- Detail-oriented and organized
- Good communication and time management

Freshers and students are welcome to apply.
"""

REQUIRED_SKILLS = [
    "typing", "data entry", "ms word", "excel", "internet browsing",
    "detail oriented", "organized", "communication", "time management"
]

def extract_text(uploaded_pdf):
    text = ""
    with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
    return text.lower()

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

def create_pdf(name, match, found, missing, summary, recs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 8, f"Resume Screening Report - {name}", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Match: {match}%", ln=1)

    pdf.ln(5)
    pdf.cell(0, 8, "Skills Found:", ln=1)
    for s in found:
        pdf.cell(0, 8, f"- {s}", ln=1)

    pdf.ln(5)
    pdf.cell(0, 8, "Missing Skills:", ln=1)
    for s in missing:
        pdf.cell(0, 8, f"- {s}", ln=1)

    pdf.ln(5)
    pdf.multi_cell(0, 8, f"Summary:\n{summary}")

    pdf.ln(5)
    pdf.multi_cell(0, 8, f"Recommendations:\n{recs}")

    return pdf.output(dest="S").encode("latin-1", errors="ignore")

st.title("✅ Resume Screener (FINAL - Streamlit Compatible)")

uploaded = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded:
    resume_text = extract_text(uploaded)
    found, missing, match = match_skills(resume_text)

    st.subheader("✅ Results")
    st.write(f"**Match: {match}%**")
    st.write(f"✅ Found: {', '.join(found)}")
    st.write(f"❌ Missing: {', '.join(missing)}")

    summary = f"The candidate matches {match}% of required job skills."
    recs = "Improve MS Word, Excel, typing speed, and organizational skills."

    report = create_pdf("Candidate", match, found, missing, summary, recs)

    st.download_button(
        "📥 Download PDF Report",
        data=report,
        file_name="resume_report.pdf",
        mime="application/pdf"
    )
else:
    st.info("Upload a PDF resume to begin.")

