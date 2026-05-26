import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="ClearSign", page_icon="📋", layout="centered")

ANTHROPIC_KEY = st.secrets["ANTHROPIC_KEY"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #f8f9ff; }
[data-testid="stSidebar"] { display: none; }

.hero { text-align: center; padding: 40px 0 28px 0; }
.hero h1 { font-size: 2.4rem; font-weight: 800; color: #1a1a2e; margin: 0; }
.hero .sub { color: #6b7280; font-size: 0.92rem; margin: 8px 0 0 0; }
.hero .badge {
    display: inline-block; background: #f0fdf4; color: #166534;
    border: 1px solid #86efac; border-radius: 999px;
    font-size: 0.75rem; font-weight: 600; padding: 4px 12px; margin-top: 10px;
}
.result-card {
    background: white; border: 1px solid #e5e7eb; border-radius: 16px;
    padding: 28px; margin-top: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.result-label {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 12px;
}
.result-text { font-size: 1.05rem; line-height: 1.75; color: #1a1a2e; }
.redflag-box {
    background: #fff1f2; border: 1px solid #fecdd3; border-left: 4px solid #f43f5e;
    border-radius: 10px; padding: 16px; margin-top: 12px;
}
.redflag-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #be123c; margin-bottom: 10px; }
.redflag-item { font-size: 0.9rem; color: #881337; padding: 5px 0;
    border-bottom: 1px solid #fecdd3; line-height: 1.5; }
.redflag-item:last-child { border-bottom: none; }
.questions-box {
    background: #eff6ff; border: 1px solid #bfdbfe; border-left: 4px solid #3b82f6;
    border-radius: 10px; padding: 16px; margin-top: 12px;
}
.questions-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #1d4ed8; margin-bottom: 10px; }
.question-item { font-size: 0.9rem; color: #1e40af; padding: 5px 0;
    border-bottom: 1px solid #bfdbfe; line-height: 1.5; }
.question-item:last-child { border-bottom: none; }
.actions-box {
    background: #f0fdf4; border: 1px solid #86efac; border-left: 4px solid #22c55e;
    border-radius: 10px; padding: 16px; margin-top: 12px;
}
.actions-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #15803d; margin-bottom: 10px; }
.action-item { font-size: 0.9rem; color: #166534; padding: 5px 0;
    border-bottom: 1px solid #86efac; line-height: 1.5; }
.action-item:last-child { border-bottom: none; }
.tldr-box {
    background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px;
    padding: 14px 16px; margin-top: 12px; font-size: 0.9rem;
    color: #166534; font-weight: 600; line-height: 1.6;
}
.analogy-box {
    background: #fff8f0; border: 1px solid #fed7aa; border-radius: 10px;
    padding: 14px 16px; margin-top: 12px; font-size: 0.9rem;
    color: #92400e; line-height: 1.6;
}
.vocab-box {
    background: #f5f3ff; border: 1px solid #c4b5fd; border-radius: 10px;
    padding: 14px 16px; margin-top: 12px; font-size: 0.88rem;
    color: #4c1d95; line-height: 1.8;
}
.upload-primary {
    background: white; border: 2px dashed #c4b5fd; border-radius: 16px;
    padding: 32px; text-align: center; margin-bottom: 16px;
}
.upload-primary h3 { color: #1a1a2e; font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }
.upload-primary p { color: #9ca3af; font-size: 0.85rem; }
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

if "history" not in st.session_state:
    st.session_state.history = []

# ── AI functions ──────────────────────────────────────────────────────────────
def explain(text, level, topic_type):
    level_prompts = {
        "5-year-old": "Explain this like I am 5 years old. Use super simple words, fun analogies, and short sentences.",
        "Middle schooler": "Explain this like I'm in middle school. Use clear simple language and relatable examples.",
        "Smart adult": "Explain this clearly for a smart adult with no background in this topic. Cut the jargon.",
        "Expert": "Give a thorough, nuanced explanation. Include key mechanics, implications, and tradeoffs."
    }
    prompt = f"""You are an expert at making complex things simple. Someone pasted this {topic_type}.

CONTENT:
{text[:3000]}

TASK: {level_prompts[level]}

Respond with EXACTLY this format:

EXPLANATION:
[3 to 6 sentences]

ANALOGY:
[One vivid analogy starting with "Think of it like..."]

TL;DR:
[One single sentence summary]

KEY TERMS:
[3-5 key terms, format: **word** — definition]"""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 800,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=25
        )
        return r.json()["content"][0]["text"]
    except:
        return None

def detect_red_flags(text, topic_type):
    prompt = f"""You are an expert analyst. Analyze this {topic_type} and find things the person should be aware of, watch out for, or question.

CONTENT:
{text[:3000]}

Find 3-5 specific flags, risks, concerns, or notable things depending on the document type:
- For contracts/legal docs: risky clauses, unusual terms, things that could hurt them
- For resumes/profiles: gaps, weaknesses, things to improve
- For financial reports: risks, red flags, concerning trends
- For news/articles: bias, missing context, claims to verify
- For emails/memos: tone issues, unclear asks, potential problems
- For medical reports: things to ask the doctor, concerning findings
- For anything else: the most important things to be aware of

Make each point specific to the actual content. Start each with ⚠️

Return ONLY a JSON array:
["⚠️ Specific point 1", "⚠️ Specific point 2", "⚠️ Specific point 3"]"""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20
        )
        txt = r.json()["content"][0]["text"].strip()
        start, end = txt.find("["), txt.rfind("]")
        if start != -1 and end != -1:
            return json.loads(txt[start:end+1])
        return []
    except:
        return []

def get_questions(text, topic_type):
    prompt = f"""You are an expert advisor. Someone just read this {topic_type}.

CONTENT:
{text[:3000]}

Give them exactly 3 smart, specific questions they should ask or think about:
- For contracts: questions to ask before signing
- For resumes: questions for an interview or self-reflection
- For financial reports: questions for an investor or analyst
- For news/articles: questions to dig deeper or verify
- For emails/memos: questions to clarify before responding
- For medical reports: questions to ask the doctor
- For anything else: the most useful follow-up questions

Make them specific to the actual content.

Return ONLY a JSON array:
["Question 1?", "Question 2?", "Question 3?"]"""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20
        )
        txt = r.json()["content"][0]["text"].strip()
        start, end = txt.find("["), txt.rfind("]")
        if start != -1 and end != -1:
            return json.loads(txt[start:end+1])
        return []
    except:
        return []

def get_action_items(text, topic_type):
    prompt = f"""You are an expert advisor. Someone just read this {topic_type}.

CONTENT:
{text[:3000]}

Give them exactly 3 concrete, specific action items — things they should actually DO:
- For contracts/legal: specific steps before signing or after
- For resumes: specific improvements to make
- For financial reports: specific things to research or act on
- For news/articles: specific things to verify or follow up on
- For emails/memos: specific things to do before responding
- For medical reports: specific things to do before the next appointment
- For anything else: the 3 most useful next steps

Make them specific to the actual content. Start each with a verb.

Return ONLY a JSON array:
["Action item 1", "Action item 2", "Action item 3"]"""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20
        )
        txt = r.json()["content"][0]["text"].strip()
        start, end = txt.find("["), txt.rfind("]")
        if start != -1 and end != -1:
            return json.loads(txt[start:end+1])
        return []
    except:
        return []

def parse_response(text):
    sections = {}
    for section in ["EXPLANATION", "ANALOGY", "TL;DR", "KEY TERMS"]:
        if section + ":" in text:
            start = text.index(section + ":") + len(section) + 1
            next_sections = [s + ":" for s in ["EXPLANATION", "ANALOGY", "TL;DR", "KEY TERMS"]
                             if s + ":" in text and text.index(s + ":") > start]
            end = text.index(next_sections[0]) if next_sections else len(text)
            sections[section] = text[start:end].strip()
    return sections

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>📋 ClearSign</h1>
    <div class="sub">Paste any document — understand it instantly, spot the risks, know what to do next</div>
    <div class="badge">✓ Red flags &nbsp;·&nbsp; ✓ Questions to ask &nbsp;·&nbsp; ✓ Action items &nbsp;·&nbsp; ✓ Compare docs</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["📄 Analyze", "🔀 Compare", "🕘 History"])

# ── TAB 1: Analyze ────────────────────────────────────────────────────────────
with tabs[0]:
    topic_type = st.selectbox(
        "What are you analyzing?",
        ["Contract", "Legal document", "Lease agreement", "Employment offer",
         "Earnings report", "Financial report", "Academic paper",
         "Email / memo", "Policy document", "Medical report",
         "Resume / profile", "News article", "Something else"]
    )

    st.markdown("""
    <div class="upload-primary">
        <h3>📎 Upload your document</h3>
        <p>PDF or Word doc — drag and drop or click to browse</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("", type=["pdf", "docx"], label_visibility="collapsed")

    text_input = ""
    if uploaded_file:
        try:
            if uploaded_file.type == "application/pdf":
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text_input = "\n".join(page.get_text() for page in doc)
            else:
                import docx as docxlib
                doc = docxlib.Document(uploaded_file)
                text_input = "\n".join(p.text for p in doc.paragraphs)
            st.success(f"✅ Loaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Could not read file: {e}")
    else:
        text_input = st.text_area(
            "Or paste text directly",
            placeholder="Paste your document, contract, article, email, or any text here...",
            height=180,
        )

    level = st.radio(
        "Explain it like I'm a...",
        ["5-year-old", "Middle schooler", "Smart adult", "Expert"],
        horizontal=True,
        index=2
    )

    show_flags     = st.checkbox("🚩 Detect red flags & things to watch out for", value=True)
    show_questions = st.checkbox("❓ Show questions to ask", value=True)
    show_actions   = st.checkbox("✅ Show action items — what to do next", value=True)

    if st.button("📋 Analyze Document"):
        if not text_input.strip():
            st.error("Upload a file or paste some text first.")
        else:
            with st.spinner("Analyzing your document..."):
                raw       = explain(text_input, level, topic_type)
                flags     = detect_red_flags(text_input, topic_type) if show_flags else []
                questions = get_questions(text_input, topic_type) if show_questions else []
                actions   = get_action_items(text_input, topic_type) if show_actions else []

            if not raw:
                st.error("Something went wrong — try again.")
            else:
                result = parse_response(raw)
                st.session_state.result    = result
                st.session_state.level     = level
                st.session_state.flags     = flags
                st.session_state.questions = questions
                st.session_state.actions   = actions

                st.session_state.history.insert(0, {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "date": datetime.now().strftime("%b %d, %Y · %I:%M %p"),
                    "topic": topic_type,
                    "snippet": text_input[:80] + "...",
                    "result": result,
                    "flags": flags,
                    "questions": questions,
                    "actions": actions,
                    "level": level,
                })
                st.session_state.history = st.session_state.history[:10]

    if st.session_state.get("result"):
        s         = st.session_state.result
        level     = st.session_state.level
        flags     = st.session_state.get("flags", [])
        questions = st.session_state.get("questions", [])
        actions   = st.session_state.get("actions", [])

        level_colors = {
            "5-year-old":      ("#fef3c7", "#92400e", "👶"),
            "Middle schooler": ("#ede9fe", "#4c1d95", "🎒"),
            "Smart adult":     ("#f0fdf4", "#166534", "🧑"),
            "Expert":          ("#eff6ff", "#1e40af", "🎓"),
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

        if flags:
            items_html = "".join([f'<div class="redflag-item">{f}</div>' for f in flags])
            st.markdown(f"""
            <div class="redflag-box">
                <div class="redflag-title">🚩 Things to Watch Out For</div>
                {items_html}
            </div>""", unsafe_allow_html=True)

        if questions:
            items_html = "".join([f'<div class="question-item">💬 {q}</div>' for q in questions])
            st.markdown(f"""
            <div class="questions-box">
                <div class="questions-title">❓ Questions to Ask</div>
                {items_html}
            </div>""", unsafe_allow_html=True)

        if actions:
            items_html = "".join([f'<div class="action-item">✅ {a}</div>' for a in actions])
            st.markdown(f"""
            <div class="actions-box">
                <div class="actions-title">✅ Action Items — What To Do Next</div>
                {items_html}
            </div>""", unsafe_allow_html=True)

        if s.get("ANALOGY"):
            st.markdown(f'<div class="analogy-box">🔍 <strong>Analogy:</strong> {s["ANALOGY"]}</div>', unsafe_allow_html=True)

        if s.get("KEY TERMS"):
            terms_html = s["KEY TERMS"].replace("\n", "<br>")
            st.markdown(f'<div class="vocab-box">📖 <strong>Key Terms:</strong><br><br>{terms_html}</div>', unsafe_allow_html=True)

        st.divider()

        if st.button("📤 Copy summary"):
            summary_text = f"📋 ClearSign Analysis\n\n"
            summary_text += f"TL;DR: {s.get('TL;DR', '')}\n\n"
            if flags:
                summary_text += "🚩 Things to Watch Out For:\n" + "\n".join(flags) + "\n\n"
            if questions:
                summary_text += "❓ Questions to Ask:\n" + "\n".join(questions) + "\n\n"
            if actions:
                summary_text += "✅ Action Items:\n" + "\n".join(actions)
            st.code(summary_text, language=None)
            st.caption("Select all and copy 👆")

        if st.button("🔄 Analyze something else"):
            for key in ["result", "level", "flags", "questions", "actions"]:
                st.session_state.pop(key, None)
            st.rerun()

# ── TAB 2: Compare ────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### 🔀 Compare Two Documents")
    st.caption("Paste two documents side by side to see how they differ.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Document A**")
        doc_a = st.text_area("", placeholder="Paste first document here...", height=250, key="doc_a")
    with col2:
        st.markdown("**Document B**")
        doc_b = st.text_area("", placeholder="Paste second document here...", height=250, key="doc_b")

    if st.button("🔀 Compare Documents"):
        if not doc_a.strip() or not doc_b.strip():
            st.error("Paste both documents first.")
        else:
            with st.spinner("Comparing..."):
                try:
                    prompt = f"""Compare these two documents and highlight the key differences.

DOCUMENT A:
{doc_a[:2000]}

DOCUMENT B:
{doc_b[:2000]}

Return ONLY a JSON object:
{{
  "summary": "One sentence on the overall difference",
  "doc_a_advantages": ["advantage 1", "advantage 2", "advantage 3"],
  "doc_b_advantages": ["advantage 1", "advantage 2", "advantage 3"],
  "key_differences": ["difference 1", "difference 2", "difference 3", "difference 4", "difference 5"]
}}"""
                    r = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"},
                        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 600,
                              "messages": [{"role": "user", "content": prompt}]},
                        timeout=25
                    )
                    txt = r.json()["content"][0]["text"].strip()
                    start, end = txt.find("{"), txt.rfind("}")
                    comp = json.loads(txt[start:end+1])

                    st.markdown(f"**Overall:** {comp.get('summary', '')}")
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**✅ Doc A has:**")
                        for a in comp.get("doc_a_advantages", []):
                            st.markdown(f"- {a}")
                    with c2:
                        st.markdown("**✅ Doc B has:**")
                        for b in comp.get("doc_b_advantages", []):
                            st.markdown(f"- {b}")
                    st.divider()
                    st.markdown("**Key differences:**")
                    for d in comp.get("key_differences", []):
                        st.markdown(f"- {d}")
                except:
                    st.error("Could not compare — try again.")

# ── TAB 3: History ────────────────────────────────────────────────────────────
with tabs[2]:
    if not st.session_state.history:
        st.info("No history yet — analyze a document to see it saved here.")
    else:
        st.caption(f"{len(st.session_state.history)} saved analyses")

        for i, item in enumerate(st.session_state.history):
            col_title, col_delete = st.columns([9, 1])
            with col_title:
                with st.expander(f"📄 {item['topic']} · {item['date']}"):
                    st.markdown(f"**Snippet:** {item['snippet']}")
                    r = item["result"]
                    if r.get("EXPLANATION"):
                        st.markdown(f"**Explanation:** {r['EXPLANATION']}")
                    if r.get("TL;DR"):
                        st.markdown(f'<div class="tldr-box">⚡ <strong>TL;DR:</strong> {r["TL;DR"]}</div>', unsafe_allow_html=True)
                    if item.get("flags"):
                        st.markdown("**🚩 Flags:**")
                        for f in item["flags"]:
                            st.markdown(f"- {f}")
                    if item.get("questions"):
                        st.markdown("**❓ Questions:**")
                        for q in item["questions"]:
                            st.markdown(f"- {q}")
                    if item.get("actions"):
                        st.markdown("**✅ Action Items:**")
                        for a in item["actions"]:
                            st.markdown(f"- {a}")
            with col_delete:
                if st.button("✕", key=f"del_{item['id']}_{i}"):
                    st.session_state.history.pop(i)
                    st.rerun()

        st.divider()
        if st.button("🗑️ Clear all history"):
            st.session_state.history = []
            st.rerun()
