import os
os.environ["THINC_NO_TORCH"] = "1"

from flask import Flask, request, render_template_string
import PyPDF2, docx, json, re
import spacy
from spacy.matcher import PhraseMatcher

# -------------------------------
# App Setup
# -------------------------------
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Load spaCy
# -------------------------------
nlp = spacy.load("en_core_web_sm")

# -------------------------------
# Skill Lists
# -------------------------------
TECHNICAL_SKILLS = [
    "python", "java", "sql", "machine learning", "deep learning",
    "data analysis", "nlp", "spacy", "flask", "django",
    "html", "css", "javascript", "git", "github"
]

SOFT_SKILLS = [
    "communication", "teamwork", "problem solving",
    "leadership", "adaptability", "time management",
    "critical thinking"
]

tech_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
soft_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

tech_matcher.add("TECH", [nlp(s) for s in TECHNICAL_SKILLS])
soft_matcher.add("SOFT", [nlp(s) for s in SOFT_SKILLS])

# -------------------------------
# Helper Functions
# -------------------------------
def file_type(name):
    if name.endswith(".txt"): return "TXT"
    if name.endswith(".pdf"): return "PDF"
    if name.endswith(".docx"): return "DOCX"
    return "NA"

def read_file(path, ftype):
    text = ""
    if ftype == "TXT":
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    elif ftype == "PDF":
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for p in reader.pages:
                if p.extract_text():
                    text += p.extract_text() + "\n"
    elif ftype == "DOCX":
        d = docx.Document(path)
        for p in d.paragraphs:
            text += p.text + "\n"
    return text

def clean_lines(text):
    return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()]

def extract_skills(text):
    doc = nlp(text.lower())
    tech, soft = set(), set()
    for _, s, e in tech_matcher(doc):
        tech.add(doc[s:e].text)
    for _, s, e in soft_matcher(doc):
        soft.add(doc[s:e].text)
    return sorted(tech), sorted(soft)

def calculate_match(resume, jd):
    if not jd:
        return 0, []
    matched = set(resume).intersection(set(jd))
    percent = round((len(matched) / len(jd)) * 100, 2)
    return percent, sorted(matched)

def overall_score(tech_pct, soft_pct):
    return round((tech_pct * 0.7) + (soft_pct * 0.3), 2)

# -------------------------------
# HTML UI (EMOJI + COLORFUL)
# -------------------------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Skill Matching System</title>
<style>
body {
    font-family: Arial;
    background: linear-gradient(to right, #e3f2fd, #fce4ec);
    padding:30px;
}

.header {
    background: linear-gradient(135deg,#3949ab,#1e88e5);
    color:white;
    padding:25px;
    border-radius:15px;
    text-align:center;
}

.upload {
    background:white;
    padding:20px;
    border-radius:15px;
    margin-top:20px;
    box-shadow:0 0 10px #bbb;
}

.container {
    display:flex;
    gap:20px;
    margin-top:20px;
}

.box {
    width:50%;
    background:white;
    border-radius:15px;
    box-shadow:0 0 10px #ccc;
}

.box h3 {
    margin:0;
    padding:15px;
    color:white;
    border-radius:15px 15px 0 0;
}

.resume { background:#1e88e5; }
.jd { background:#8e24aa; }
.match { background:#ff7043; }
.skills { background:#2e7d32; }

.content {
    padding:15px;
    max-height:350px;
    overflow:auto;
}

.skill {
    display:inline-block;
    background:#e8f5e9;
    color:#1b5e20;
    padding:8px 12px;
    margin:6px;
    border-radius:20px;
    font-weight:bold;
}

.score {
    font-size:32px;
    font-weight:bold;
    color:#2e7d32;
    text-align:center;
}

button {
    background:#3949ab;
    color:white;
    border:none;
    padding:12px 25px;
    border-radius:8px;
    cursor:pointer;
    font-size:16px;
}
</style>
</head>

<body>

<div class="header">
<h1>🎯 Resume & JD Skill Matching System</h1>
<p>📄 Upload Resume | 📋 Job Description | 🧠 NLP Analysis</p>
</div>

<div class="upload">
<form method="POST" enctype="multipart/form-data">
📄 <b>Resume:</b>
<input type="file" name="resume" required>
&nbsp;&nbsp;
📋 <b>Job Description:</b>
<input type="file" name="jd" required>
<br><br>
<button>🚀 Upload & Analyze</button>
</form>
</div>

{% if resume_lines %}
<div class="container">
<div class="box">
<h3 class="resume">📄 Resume Content</h3>
<div class="content">{% for l in resume_lines %}<p>{{ l }}</p>{% endfor %}</div>
</div>

<div class="box">
<h3 class="jd">📋 Job Description</h3>
<div class="content">{% for l in jd_lines %}<p>{{ l }}</p>{% endfor %}</div>
</div>
</div>

<div class="container">
<div class="box">
<h3 class="match">📊 Overall Matching Score</h3>
<div class="content">
<p class="score">{{ overall }}%</p>
<p>🛠 <b>Technical Match:</b> {{ tech_pct }}%</p>
<p>🤝 <b>Soft Skill Match:</b> {{ soft_pct }}%</p>
</div>
</div>

<div class="box">
<h3 class="skills">🛠 Matched Technical Skills</h3>
<div class="content">
{% for s in tech_matched %}<span class="skill">⚙ {{ s }}</span>{% endfor %}
</div>
</div>
</div>

<div class="container">
<div class="box">
<h3 class="skills">🤝 Matched Soft Skills</h3>
<div class="content">
{% for s in soft_matched %}<span class="skill">💡 {{ s }}</span>{% endfor %}
</div>
</div>
</div>
{% endif %}

</body>
</html>
"""

# -------------------------------
# Flask Route
# -------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    resume_lines = jd_lines = None
    tech_pct = soft_pct = overall = 0
    tech_matched = soft_matched = []

    if request.method == "POST":
        r = request.files["resume"]
        j = request.files["jd"]

        r_path = os.path.join(UPLOAD_FOLDER, r.filename)
        j_path = os.path.join(UPLOAD_FOLDER, j.filename)
        r.save(r_path)
        j.save(j_path)

        r_text = read_file(r_path, file_type(r.filename.lower()))
        j_text = read_file(j_path, file_type(j.filename.lower()))

        resume_lines = clean_lines(r_text)
        jd_lines = clean_lines(j_text)

        r_tech, r_soft = extract_skills(r_text)
        j_tech, j_soft = extract_skills(j_text)

        tech_pct, tech_matched = calculate_match(r_tech, j_tech)
        soft_pct, soft_matched = calculate_match(r_soft, j_soft)

        overall = overall_score(tech_pct, soft_pct)

    return render_template_string(
        HTML,
        resume_lines=resume_lines,
        jd_lines=jd_lines,
        tech_matched=tech_matched,
        soft_matched=soft_matched,
        tech_pct=tech_pct,
        soft_pct=soft_pct,
        overall=overall
    )

if __name__ == "__main__":
    app.run(debug=True)
