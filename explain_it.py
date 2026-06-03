"""
ClearSign — Understand any document before you sign.

Drop-in replacement for the live Streamlit app. Keeps the existing infrastructure
(st.secrets["ANTHROPIC_KEY"], direct REST calls via requests, PyMuPDF for PDF) so it
redeploys without changes, while upgrading the product:

  • Fixed the invisible-label bug — everything is high-contrast and readable.
  • Grounded red flags: each one quotes the exact clause, with a severity badge,
    a plain-English consequence, and a concrete "what to ask for" redline.
  • A 0-100 risk score + "who it favors" verdict.
  • Version compare that says whether v2 got better or WORSE for you, per change.
  • Session history + one-click Markdown export.

Not legal advice.
"""

import io
import json
from datetime import datetime

import requests
import streamlit as st

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="ClearSign — understand any document", page_icon="📋", layout="centered")

# Match the existing secret name; fall back to the SDK-style name just in case.
ANTHROPIC_KEY = st.secrets.get("ANTHROPIC_KEY") or st.secrets.get("ANTHROPIC_API_KEY")

MODEL = "claude-haiku-4-5-20251001"  # proven on this account; fast + cheap
API_URL = "https://api.anthropic.com/v1/messages"

DOC_TYPES = {
    "Auto-detect": "Detect the document type yourself and analyze accordingly.",
    "Service / freelance agreement": "Focus on scope creep, payment & kill fees, IP ownership, indemnification, termination.",
    "Vendor / SaaS contract": "Focus on auto-renewal, price-increase rights, data ownership, liability caps, SLAs, termination for convenience.",
    "Employment / offer letter": "Focus on at-will clauses, non-competes, IP assignment, equity vesting, severance, arbitration.",
    "NDA": "Focus on the definition of confidential info, term length, residuals, non-solicit, one-sided obligations.",
    "Lease / rental": "Focus on auto-renewal, fees, repair duties, early-termination penalties, entry rights.",
    "Terms of Service": "Focus on arbitration, class-action waivers, data/privacy rights, unilateral changes, account termination.",
    "Other / general": "Analyze as a general contract; surface anything one-sided or unusual.",
}

SEVERITY = {
    "high":   {"label": "High risk",    "color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca", "dot": "🔴"},
    "medium": {"label": "Worth noting", "color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "dot": "🟠"},
    "low":    {"label": "Minor",        "color": "#2563eb", "bg": "#eff6ff", "border": "#bfdbfe", "dot": "🔵"},
}

# --------------------------------------------------------------------------- #
# Styling — explicit colors so nothing renders white-on-white
# --------------------------------------------------------------------------- #

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #f8fafc; }
[data-testid="stSidebar"] { display: none; }

/* Force readable text on every control — this is the invisible-label fix */
html, body, [class*="css"], .stMarkdown, label, p, span, li,
.stRadio label, .stCheckbox label, .stSelectbox label, .stTextArea label,
.stFileUploader label, .stTabs [data-baseweb="tab"], .stRadio div, .stCheckbox div {
    color: #0f172a !important;
}
.block-container { max-width: 880px; padding-top: 1.8rem; }

.hero { text-align: center; padding: 8px 0 6px; }
.hero h1 { font-size: 2.5rem; font-weight: 800; color: #0f172a; margin: 0; letter-spacing: -.02em; }
.hero .tag { color: #0f172a; font-weight: 600; font-size: 1.12rem; margin-top: 4px; }
.hero .sub { color: #475569; font-size: .95rem; margin: 6px auto 0; max-width: 560px; }
.pills { text-align: center; margin: 12px 0 18px; }
.pill { display:inline-block; background:#eef2ff; color:#4f46e5 !important; border-radius:999px;
        padding:4px 11px; margin:3px; font-size:.8rem; font-weight:600; }

.stButton > button { background:#4f46e5 !important; color:#fff !important; border:0 !important;
        border-radius:10px !important; font-weight:700 !important; font-size:1rem !important;
        padding:11px 22px !important; width:100% !important; }
.stButton > button:hover { background:#4338ca !important; }
.stTextArea textarea { background:#fff !important; border:1.5px solid #e2e8f0 !important;
        border-radius:10px !important; color:#0f172a !important; font-size:.92rem !important; }
.stSelectbox > div > div { background:#fff !important; border:1.5px solid #e2e8f0 !important; border-radius:10px !important; }
/* Selected value shown in the closed select */
.stSelectbox div[data-baseweb="select"] div, .stSelectbox div[data-baseweb="select"] span { color:#0f172a !important; }
/* Open dropdown menu (renders in a portal with a dark bg by default) */
div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] { background:#ffffff !important; border:1px solid #e2e8f0 !important; }
ul[role="listbox"] li, li[role="option"] { background:#ffffff !important; color:#0f172a !important; }
ul[role="listbox"] li:hover, li[role="option"]:hover, li[aria-selected="true"] { background:#eef2ff !important; color:#0f172a !important; }
/* Download button readability */
.stDownloadButton > button { background:#fff !important; color:#0f172a !important; border:1.5px solid #e2e8f0 !important; border-radius:10px !important; font-weight:600 !important; }
.stDownloadButton > button:hover { background:#f1f5f9 !important; color:#0f172a !important; }

.card { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:16px 18px; margin-top:12px; }
.flag-title { font-weight:700; font-size:1.02rem; margin:2px 0; color:#0f172a; }
.quote { border-left:3px solid #e2e8f0; padding:6px 11px; margin:8px 0; background:#f8fafc;
         color:#475569; font-style:italic; border-radius:4px; font-size:.9rem; }
.lab { font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; color:#475569; font-weight:700; }
.badge { display:inline-block; border-radius:999px; padding:2px 9px; font-size:.74rem; font-weight:700; }
.score-num { font-size:3rem; font-weight:800; line-height:1; }
.score-cap { color:#475569; font-size:.88rem; }
.foot { color:#475569; font-size:.8rem; text-align:center; margin-top:28px; }
hr { border-color:#e2e8f0 !important; }
.stTabs [data-baseweb="tab-list"] { gap:22px; }
.stTabs [data-baseweb="tab"] { font-weight:600 !important; }
.stTabs [aria-selected="true"] { color:#4f46e5 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>📋 ClearSign</h1>
  <div class="tag">Understand any document before you sign.</div>
  <div class="sub">Paste it or upload it. Get the risks, the questions to ask, and what to do next — in plain English.</div>
</div>
<div class="pills">
  <span class="pill">⚖️ Risk score</span>
  <span class="pill">🚩 Grounded red flags</span>
  <span class="pill">❓ Questions to ask</span>
  <span class="pill">✅ Action items</span>
  <span class="pill">🔀 Version compare</span>
</div>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _call_claude(prompt, max_tokens=4000, system=None):
    if not ANTHROPIC_KEY:
        st.error("No API key found. Add ANTHROPIC_KEY to your Streamlit secrets and reload.")
        st.stop()
    body = {"model": MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    r = requests.post(
        API_URL,
        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY,
                 "anthropic-version": "2023-06-01"},
        json=body, timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def _parse_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw
        raw = raw.replace("json", "", 1).strip() if raw.lstrip().startswith("json") else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1:
            try:
                return json.loads(raw[s:e + 1])
            except json.JSONDecodeError:
                pass
    return {"_error": "Could not parse the response. Try again.", "_raw": raw[:1500]}


def extract_text(uploaded):
    name = (uploaded.name or "").lower()
    data = uploaded.read()
    if name.endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=data, filetype="pdf")
            return "\n".join(page.get_text() for page in doc).strip()
        except Exception:
            return ""
    if name.endswith(".docx"):
        try:
            import docx as docxlib
            d = docxlib.Document(io.BytesIO(data))
            return "\n".join(p.text for p in d.paragraphs).strip()
        except Exception:
            return ""
    try:
        return data.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


ANALYSIS_PROMPT = """You are ClearSign, a sharp contract analyst who explains documents to non-lawyers.
You are precise and NEVER invent clauses — every finding is tied to the exact text. Not legal advice.

Document type context: {dt}. {focus}
Review depth: {depth}.

Return ONLY valid JSON (no markdown fences) of this exact shape:
{{
  "doc_type": "your best guess at what this document is",
  "summary": "2-3 plain-English sentences a non-lawyer understands",
  "risk_score": 0,
  "risk_label": "e.g. 'Mostly standard', 'Several concerns', 'High risk'",
  "who_it_favors": "'you', 'the other party', or 'balanced' + one clause why",
  "red_flags": [
    {{"title": "short label",
      "severity": "high|medium|low",
      "quote": "EXACT text from the document this is based on (verbatim, trim with …)",
      "why": "plain-English real-world consequence for the reader",
      "suggested_ask": "concrete redline or question to send the other party"}}
  ],
  "questions": ["specific questions to ask before signing"],
  "action_items": ["concrete next steps, most important first"]
}}
Rules: every red_flag.quote MUST be copied from the document; if you can't ground it, drop it.
3-8 red flags max. Be concrete. No disclaimers inside fields.

DOCUMENT:
\"\"\"
{text}
\"\"\""""

COMPARE_PROMPT = """You are ClearSign comparing two versions of a document for a non-lawyer.
For each meaningful change, say whether it is better or WORSE FOR THE READER and why.
Ground every change in the actual text. Not legal advice.

Return ONLY valid JSON (no fences):
{{
  "overall": "1-2 sentence verdict: did version B get better or worse for the reader?",
  "verdict": "better|worse|mixed|no_material_change",
  "changes": [
    {{"what": "what changed, plainly",
      "direction": "better|worse|neutral",
      "from": "short quote/paraphrase of A",
      "to": "short quote/paraphrase of B",
      "impact": "why it matters to the reader"}}
  ]
}}
Material changes only; ignore pure formatting.

VERSION A (older):
\"\"\"
{a}
\"\"\"

VERSION B (newer):
\"\"\"
{b}
\"\"\""""


def render_result(res):
    if "_error" in res:
        st.error(res["_error"])
        return

    score = int(res.get("risk_score", 0) or 0)
    color = "#dc2626" if score >= 67 else "#d97706" if score >= 34 else "#16a34a"
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f'<div style="text-align:center"><div class="score-num" style="color:{color}">{score}</div>'
                    f'<div class="score-cap">risk / 100</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"**{res.get('risk_label','')}**")
        if res.get("who_it_favors"):
            st.markdown(f"**Favors:** {res['who_it_favors']}")
        if res.get("doc_type"):
            st.caption(f"Detected as: {res['doc_type']}")

    if res.get("summary"):
        st.markdown("#### In plain English")
        st.write(res["summary"])

    flags = res.get("red_flags", []) or []
    if flags:
        st.markdown(f"#### 🚩 Red flags ({len(flags)})")
        for f in flags:
            m = SEVERITY.get((f.get("severity") or "medium").lower(), SEVERITY["medium"])
            q = (f.get("quote") or "").strip()
            st.markdown(
                f"""<div class="card" style="border-left:5px solid {m['color']}">
                    <span class="badge" style="background:{m['bg']};color:{m['color']};border:1px solid {m['border']}">{m['dot']} {m['label']}</span>
                    <div class="flag-title">{f.get('title','')}</div>
                    {f'<div class="quote">“{q}”</div>' if q else ''}
                    <div><span class="lab">What it means</span><br>{f.get('why','')}</div>
                    {f'<div style="margin-top:8px"><span class="lab">What to ask for</span><br>{f.get("suggested_ask","")}</div>' if f.get('suggested_ask') else ''}
                </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if res.get("questions"):
            st.markdown("#### ❓ Questions to ask")
            for q in res["questions"]:
                st.markdown(f"- {q}")
    with col2:
        if res.get("action_items"):
            st.markdown("#### ✅ Action items")
            for a in res["action_items"]:
                st.markdown(f"- {a}")


def result_to_markdown(res):
    L = [f"# ClearSign analysis — {res.get('doc_type','document')}", "",
         f"**Risk score:** {res.get('risk_score','?')}/100 — {res.get('risk_label','')}",
         f"**Favors:** {res.get('who_it_favors','')}", "", "## Summary", res.get("summary", ""), "", "## Red flags"]
    for f in res.get("red_flags", []) or []:
        L.append(f"### [{(f.get('severity') or '').upper()}] {f.get('title','')}")
        if f.get("quote"):
            L.append(f"> {f['quote']}")
        L.append(f"- **What it means:** {f.get('why','')}")
        if f.get("suggested_ask"):
            L.append(f"- **What to ask for:** {f['suggested_ask']}")
        L.append("")
    L += ["## Questions to ask"] + [f"- {q}" for q in res.get("questions", []) or []]
    L += ["", "## Action items"] + [f"- {a}" for a in res.get("action_items", []) or []]
    L += ["", "---", "_Generated by ClearSign. Informational only — not legal advice._"]
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #

tabs = st.tabs(["📋 Analyze", "🔀 Compare versions", "🕘 History"])

# ---- Analyze ----
with tabs[0]:
    cL, cR = st.columns([2, 1])
    with cL:
        doc_label = st.selectbox("Document type", list(DOC_TYPES.keys()), index=0,
                                 help="Tunes what ClearSign looks for.")
    with cR:
        depth = st.radio("Depth", ["Quick scan", "Standard", "Deep review"], index=1)

    up = st.file_uploader("Upload a file (optional)", type=["pdf", "docx", "txt"])
    text = st.text_area("…or paste the text here", height=220,
                        placeholder="Paste your contract, agreement, lease, or terms of service…")

    if up is not None:
        ex = extract_text(up)
        if ex:
            text = ex
            st.success(f"Loaded {len(ex):,} characters from {up.name}.")
        else:
            st.warning(f"Couldn't read text from {up.name}. If it's a scanned PDF, paste the text instead.")

    if st.button("📋 Analyze document"):
        if not text or len(text.strip()) < 40:
            st.warning("Please paste or upload a document with a bit more text.")
        else:
            with st.spinner("Reading every clause…"):
                try:
                    raw = _call_claude(ANALYSIS_PROMPT.format(
                        dt=doc_label, focus=DOC_TYPES[doc_label], depth=depth, text=text.strip()[:60000]))
                    res = _parse_json(raw)
                except Exception as e:
                    res = {"_error": f"Request failed: {e}"}
            st.session_state.last_result = res
            if "_error" not in res:
                st.session_state.history.insert(0, {
                    "title": (res.get("doc_type") or doc_label or "Document")[:60],
                    "when": datetime.now().strftime("%b %d, %I:%M %p"),
                    "result": res,
                })
                st.session_state.history = st.session_state.history[:15]

    if st.session_state.get("last_result"):
        st.divider()
        render_result(st.session_state.last_result)
        if "_error" not in st.session_state.last_result:
            st.download_button("⬇️ Download analysis (Markdown)",
                               result_to_markdown(st.session_state.last_result),
                               file_name="clearsign-analysis.md", mime="text/markdown")

# ---- Compare ----
with tabs[1]:
    st.markdown("Paste two versions of a document. ClearSign tells you **what changed and whether it got better or worse for you.**")
    a_col, b_col = st.columns(2)
    with a_col:
        va = st.text_area("Version A (older)", height=240, key="cmp_a")
    with b_col:
        vb = st.text_area("Version B (newer)", height=240, key="cmp_b")

    if st.button("🔀 Compare versions"):
        if len(va.strip()) < 40 or len(vb.strip()) < 40:
            st.warning("Paste both versions (a bit more text needed).")
        else:
            with st.spinner("Diffing the meaning, not just the words…"):
                try:
                    raw = _call_claude(COMPARE_PROMPT.format(a=va.strip()[:30000], b=vb.strip()[:30000]),
                                       max_tokens=3000)
                    res = _parse_json(raw)
                except Exception as e:
                    res = {"_error": f"Request failed: {e}"}
            if "_error" in res:
                st.error(res["_error"])
            else:
                vmap = {"better": ("#16a34a", "Better for you ✅"), "worse": ("#dc2626", "Worse for you ⚠️"),
                        "mixed": ("#d97706", "Mixed 🟠"), "no_material_change": ("#475569", "No material change")}
                vc, vl = vmap.get(res.get("verdict", ""), ("#475569", res.get("verdict", "")))
                st.markdown(f"<h4 style='color:{vc}'>{vl}</h4>", unsafe_allow_html=True)
                st.write(res.get("overall", ""))
                for ch in res.get("changes", []) or []:
                    dc = {"better": "#16a34a", "worse": "#dc2626", "neutral": "#475569"}.get(ch.get("direction", "neutral"), "#475569")
                    st.markdown(
                        f"""<div class="card" style="border-left:5px solid {dc}">
                            <div class="flag-title">{ch.get('what','')}</div>
                            <div class="quote">A: {ch.get('from','')}<br>B: {ch.get('to','')}</div>
                            <div><span class="lab">Impact</span><br>{ch.get('impact','')}</div>
                        </div>""", unsafe_allow_html=True)

# ---- History ----
with tabs[2]:
    if not st.session_state.history:
        st.info("Your analyses from this session will show up here.")
    else:
        st.caption(f"{len(st.session_state.history)} analyses this session")
        for i, item in enumerate(st.session_state.history):
            with st.expander(f"📄 {item['title']} · risk {item['result'].get('risk_score','?')}/100 · {item['when']}"):
                render_result(item["result"])
        if st.button("🗑️ Clear history"):
            st.session_state.history = []
            st.rerun()

st.markdown('<div class="foot">ClearSign gives you information, not legal advice. '
            'For high-stakes decisions, talk to a lawyer.</div>', unsafe_allow_html=True)
