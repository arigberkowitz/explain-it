import streamlit as st
import requests

st.set_page_config(page_title="Explain It", page_icon="🧠", layout="centered")

ANTHROPIC_KEY = st.secrets["ANTHROPIC_KEY"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #f8f9ff; }
[data-testid="stSidebar"] { display: none; }

.hero { text-align: center; padding: 40px 0 28px 0; }
.hero h1 { font-size: 2.2rem; font-weight: 800; color: #1a1a2e; margin: 0; }
.hero p { color: #6b7280; font-size: 0.92rem; margin: 8px 0 0 0; }

.level-btn { 
    display: inline-block; padding: 8px 18px; border-radius: 999px; 
    font-size: 0.82rem; font-weight: 700; cursor: pointer; margin: 4px;
    border: 2px solid transparent;
}

.result-card {
    background: white; border: 1px solid #e5e7eb; border-radius: 16px;
    padding: 28px 28px; margin-top: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.result-label {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 12px;
}
.result-text {
    font-size: 1.05rem; line-height: 1.75; color: #1a1a2e;
}

.analogy-box {
    background: #fff8f0; border: 1px solid #fed7aa; border-radius: 10px;
    padding: 14px 16px; margin-top: 16px; font-size: 0.9rem; 
    color: #92400e; line-height: 1.6;
}
.tldr-box {
    background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px;
    padding: 14px 16px; margin-top: 12px; font-size: 0.9rem;
    color: #166534; font-weight: 600; line-height: 1.6;
}
.vocab-box {
    background: #f5f3ff; border: 1px solid #c4b5fd; border-radius: 10px;
    padding: 14px 16px; margin-top: 12px; font-size: 0.88rem;
    color: #4c1d95; line-height: 1.8;
}

.stButton > button {
    background: #6366f1 !important; color: white !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; font-size: 1rem !important;
    padding: 12px 28px !important; width: 100% !important;
}
.stButton > button:hover { background: #4f46e5 !important; }
.stTextArea textarea {
    background: white !important; border: 1.5px solid #e5e7eb !important;
    border-radius: 10px !important; color: #1a1a2e !important;
    font-size: 0.92rem !important; line-height: 1.6 !important;
}
.stSelectbox > div > div {
    background: white !important; border: 1.5px solid #e5e7eb !important;
    border-radius: 10px !important;
}
hr { border-color: #e5e7eb !important; }
</style>
""", unsafe_allow_html=True)

def explain(text, level, topic_type):
    level_prompts = {
        "5-year-old": "Explain this like I am 5 years old. Use super simple words, fun analogies, and short sentences. Avoid any jargon completely.",
        "Middle schooler": "Explain this like I'm in middle school. Use clear simple language, relatable examples, and avoid technical jargon.",
        "Smart adult": "Explain this clearly and concisely for a smart adult with no background in this topic. Cut the jargon, keep it practical.",
        "Expert": "Give a thorough, nuanced explanation for someone who wants to deeply understand this. Include key mechanics, implications, and tradeoffs."
    }

    prompt = f"""You are an expert at making complex things simple. Someone pasted this {topic_type} and wants it explained.

CONTENT:
{text[:3000]}

TASK: {level_prompts[level]}

Respond with EXACTLY this format — no extra text:

EXPLANATION:
[Your clear explanation here — 3 to 6 sentences depending on complexity]

ANALOGY:
[One vivid real-world analogy that makes this click. Start with "Think of it like..."]

TL;DR:
[One single sentence. The absolute core of what this is saying.]

KEY TERMS:
[3-5 important words or phrases from the content, each with a one-sentence plain-English definition. Format: **word** — definition]"""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 800,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=25
        )
        return r.json()["content"][0]["text"]
    except Exception as e:
        return None

def parse_response(text):
    sections = {}
    for section in ["EXPLANATION", "ANALOGY", "TL;DR", "KEY TERMS"]:
        if section + ":" in text:
            start = text.index(section + ":") + len(section) + 1
            next_sections = [s + ":" for s in ["EXPLANATION", "ANALOGY", "TL;DR", "KEY TERMS"] if s + ":" in text and text.index(s + ":") > start]
            end = text.index(next_sections[0]) if next_sections else len(text)
            sections[section] = text[start:end].strip()
    return sections

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🧠 Explain It</h1>
    <p>Paste anything confusing — earnings report, legal doc, news article, contract, email — and get it explained simply</p>
</div>
""", unsafe_allow_html=True)

topic_type = st.selectbox(
    "What are you pasting?",
    ["Earnings report", "Legal document", "News article", "Contract", "Financial report",
     "Academic paper", "Email / memo", "Policy document", "Medical report", "Something else"]
)

uploaded_file = st.file_uploader(
    "Upload a file (PDF or Word doc)",
    type=["pdf", "docx"]
)

if uploaded_file:
    import fitz
    import docx as docxlib
    if uploaded_file.type == "application/pdf":
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text_input = "\n".join(page.get_text() for page in doc)
    else:
        doc = docxlib.Document(uploaded_file)
        text_input = "\n".join(p.text for p in doc.paragraphs)
    st.success(f"File loaded: {uploaded_file.name}")
else:
    text_input = st.text_area(
        "",
        placeholder="Or paste your text here...",
        height=200,
        label_visibility="collapsed"
    )

level = st.radio(
    "Explain it like I'm a...",
    ["5-year-old", "Middle schooler", "Smart adult", "Expert"],
    horizontal=True,
    index=2
)

if st.button("🧠 Explain This"):
    if not text_input.strip():
        st.error("Paste some text first.")
    else:
        with st.spinner("Breaking it down..."):
            raw = explain(text_input, level, topic_type)

        if not raw:
            st.error("Something went wrong — try again.")
        else:
            st.session_state.result = parse_response(raw)
            st.session_state.level  = level

if st.session_state.get("result"):
    s     = st.session_state.result
    level = st.session_state.level

    level_colors = {
        "5-year-old":    ("#fef3c7", "#92400e", "👶"),
        "Middle schooler": ("#ede9fe", "#4c1d95", "🎒"),
        "Smart adult":   ("#f0fdf4", "#166534", "🧑"),
        "Expert":        ("#eff6ff", "#1e40af", "🎓"),
    }
    bg, fg, emoji = level_colors.get(level, ("#f9fafb", "#374151", "🧠"))

    st.markdown(f"""
    <div class="result-card">
        <div class="result-label" style="color:{fg};">{emoji} Explained for a {level}</div>
        <div class="result-text">{s.get("EXPLANATION", "")}</div>
    </div>
    """, unsafe_allow_html=True)

    if s.get("TL;DR"):
        st.markdown(f'<div class="tldr-box">⚡ <strong>TL;DR:</strong> {s["TL;DR"]}</div>', unsafe_allow_html=True)

    if s.get("ANALOGY"):
        st.markdown(f'<div class="analogy-box">🔍 <strong>Analogy:</strong> {s["ANALOGY"]}</div>', unsafe_allow_html=True)

    if s.get("KEY TERMS"):
        terms_html = s["KEY TERMS"].replace("\n", "<br>")
        st.markdown(f'<div class="vocab-box">📖 <strong>Key Terms:</strong><br><br>{terms_html}</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("🔄 Explain something else"):
        st.session_state.pop("result", None)
        st.rerun()
