import streamlit as st
import json, csv, io, sys, os, math
from datetime import date

st.set_page_config(
    page_title="DeepMatch — Candidate Ranker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .block-container { padding-top: 2rem; max-width: 1200px; }

    .hero-title {
        font-size: 2.4rem; font-weight: 800; color: #ffffff;
        letter-spacing: -0.5px; margin-bottom: 0;
    }
    .hero-sub {
        font-size: 1rem; color: #8b8fa8; margin-top: 4px; margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1e2130; border-radius: 12px; padding: 1.2rem 1.5rem;
        border: 1px solid #2d3148; text-align: center;
    }
    .metric-val  { font-size: 2rem; font-weight: 700; color: #7c6ff5; }
    .metric-label { font-size: 0.8rem; color: #8b8fa8; margin-top: 2px; }

    .cand-card {
        background: #1a1d2e; border-radius: 10px; padding: 1rem 1.2rem;
        border: 1px solid #2a2d45; margin-bottom: 0.6rem;
        transition: border-color 0.2s;
    }
    .cand-card:hover { border-color: #7c6ff5; }
    .cand-rank  { font-size: 0.75rem; color: #8b8fa8; font-weight: 600; }
    .cand-name  { font-size: 1rem; font-weight: 700; color: #e8e9f0; margin: 2px 0; }
    .cand-meta  { font-size: 0.8rem; color: #8b8fa8; }
    .cand-reason { font-size: 0.8rem; color: #a0a4be; margin-top: 6px;
                   border-top: 1px solid #2a2d45; padding-top: 6px; }
    .score-pill {
        display: inline-block; padding: 2px 10px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 700;
    }
    .score-high { background: #1a3a2a; color: #4ade80; }
    .score-med  { background: #2a2a1a; color: #facc15; }
    .score-low  { background: #2a1a1a; color: #f87171; }
    .skill-tag {
        display: inline-block; background: #252840; color: #a5b4fc;
        border-radius: 4px; padding: 1px 7px; font-size: 0.72rem;
        margin-right: 4px; margin-top: 3px;
    }
    .jd-box {
        background: #1e2130; border-radius: 10px; padding: 1rem 1.2rem;
        border-left: 3px solid #7c6ff5; font-size: 0.82rem; color: #a0a4be;
        line-height: 1.6;
    }
    .section-header {
        font-size: 0.7rem; font-weight: 700; color: #7c6ff5;
        letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 0.5rem;
    }
    div[data-testid="stFileUploader"] { margin-top: 0.5rem; }
    .stButton > button {
        background: linear-gradient(135deg, #7c6ff5, #5b52e0);
        color: white; border: none; border-radius: 8px;
        padding: 0.5rem 2rem; font-weight: 600; width: 100%;
    }
    .stButton > button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">Target Role</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="jd-box">
<b style="color:#e8e9f0">Senior AI Engineer</b><br>
Redrob AI · Founding Team<br>
Pune / Noida · Hybrid · 5-9 yrs<br><br>
<b style="color:#c4c6d8">Must have</b><br>
• Embeddings-based retrieval in prod<br>
• Vector DB (FAISS, Pinecone, Qdrant…)<br>
• Strong Python + eval frameworks<br>
• NDCG / MRR / MAP experience<br><br>
<b style="color:#c4c6d8">Nice to have</b><br>
• LLM fine-tuning (LoRA, QLoRA)<br>
• Learning-to-rank, HR-tech<br>
• Open-source contributions
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">How it works</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="font-size:0.8rem; color:#8b8fa8; line-height:1.7">
<b style="color:#c4c6d8">Stage 1</b> · Structured pre-filter<br>
Skills · Experience · Signals · Career<br><br>
<b style="color:#c4c6d8">Stage 2</b> · Semantic scoring<br>
sentence-transformers MiniLM-L6<br><br>
<b style="color:#c4c6d8">Stage 3</b> · Multi-signal combine<br>
0.35 sem + 0.28 skills + 0.14 career<br>
+ 0.12 behavioral + 0.06 exp + 0.05 loc<br><br>
<b style="color:#c4c6d8">Honeypot detection</b> on all candidates
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.caption("🏆 India Runs · Track 1 · Team DeepMatch")

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🎯 DeepMatch</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Intelligent Candidate Discovery — beyond keyword filters</div>',
            unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
col_up, col_btn = st.columns([3, 1])
with col_up:
    uploaded = st.file_uploader(
        "Upload candidates (JSONL)",
        type=["jsonl", "json"],
        label_visibility="collapsed",
        help="One JSON candidate object per line. Use sample_candidates.json from the bundle."
    )
with col_btn:
    run_btn = st.button("🚀 Rank Candidates", disabled=uploaded is None)

if not uploaded:
    st.markdown("""
<div style="background:#1a1d2e; border-radius:10px; padding:2rem; text-align:center;
            border: 1px dashed #2a2d45; color:#8b8fa8; margin-top:1rem;">
    <div style="font-size:2rem">📂</div>
    <div style="font-size:0.9rem; margin-top:0.5rem">
        Upload <code>sample_candidates.json</code> from the hackathon bundle to try the ranker
    </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ── Load candidates ──────────────────────────────────────────────────────────
raw = uploaded.read().decode("utf-8")
candidates = []
for line in raw.strip().splitlines():
    line = line.strip()
    if line:
        try:
            candidates.append(json.loads(line))
        except Exception:
            pass

st.markdown(f'<div style="color:#8b8fa8; font-size:0.8rem; margin-bottom:1rem">'
            f'📋 {len(candidates)} candidates loaded from <b style="color:#c4c6d8">'
            f'{uploaded.name}</b></div>', unsafe_allow_html=True)

if not run_btn:
    st.stop()

# ── Run ranking ───────────────────────────────────────────────────────────────
with st.spinner("Ranking candidates..."):
    sys.path.insert(0, os.path.dirname(__file__) or ".")
    from rank import (score_skills, score_experience, score_behavioral,
                      score_career, score_location, honeypot_penalty, make_reasoning)

    results = []
    for c in candidates:
        sk, matched = score_skills(c)
        exp         = score_experience(c)
        beh         = score_behavioral(c)
        car, hprod  = score_career(c)
        loc         = score_location(c)
        hp          = honeypot_penalty(c)

        raw_score = (0.35*sk + 0.20*exp + 0.20*beh + 0.15*car + 0.10*loc)
        final     = round(raw_score * (1.0 - 0.65*hp), 4)

        results.append({
            "candidate_id": c["candidate_id"],
            "score": final,
            "matched": matched,
            "has_prod": hprod,
            "hp": hp,
            "candidate": c,
        })

    results.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    top_n = results[:100]

# ── Metrics ───────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
scores = [r["score"] for r in top_n]
honeypots_flagged = sum(1 for r in top_n if r["hp"] >= 0.5)

with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-val">{len(candidates)}</div>'
                f'<div class="metric-label">Candidates scanned</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div class="metric-val">{len(top_n)}</div>'
                f'<div class="metric-label">Shortlisted</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><div class="metric-val">{scores[0]:.3f}</div>'
                f'<div class="metric-label">Top score</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><div class="metric-val">'
                f'<span style="color:{"#f87171" if honeypots_flagged else "#4ade80"}">'
                f'{honeypots_flagged}</span></div>'
                f'<div class="metric-label">Honeypots flagged</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Results ───────────────────────────────────────────────────────────────────
col_list, col_detail = st.columns([5, 3])

with col_list:
    st.markdown('<div class="section-header">Ranked Shortlist</div>', unsafe_allow_html=True)

    for item in top_n:
        p   = item["candidate"]["profile"]
        s   = item["candidate"]["redrob_signals"]
        sc  = item["score"]

        pill_cls = "score-high" if sc >= 0.70 else ("score-med" if sc >= 0.50 else "score-low")
        skills_html = "".join(
            f'<span class="skill-tag">{sk}</span>'
            for sk in (item["matched"] or [])[:4]
        )
        open_badge = ('&nbsp;🟢 Open' if s.get("open_to_work_flag") else
                      '<span style="color:#555">🔴 Closed</span>')
        gh = s.get("github_activity_score", -1)
        gh_badge = f'&nbsp;·&nbsp;⭐ GH {gh:.0f}' if gh >= 0 else ""

        reason = make_reasoning(item["candidate"], item["matched"], item["has_prod"])

        st.markdown(f"""
<div class="cand-card">
  <div style="display:flex; justify-content:space-between; align-items:flex-start">
    <div>
      <div class="cand-rank">#{item["candidate_id"]} &nbsp;·&nbsp; Rank {top_n.index(item)+1}</div>
      <div class="cand-name">{p.get("current_title","Engineer")}</div>
      <div class="cand-meta">
        {p.get("years_of_experience",0):.1f} yrs &nbsp;·&nbsp;
        {p.get("location","")}, {p.get("country","")}
        &nbsp;·&nbsp; {open_badge}{gh_badge}
      </div>
    </div>
    <div><span class="score-pill {pill_cls}">{sc:.3f}</span></div>
  </div>
  <div style="margin-top:6px">{skills_html}</div>
  <div class="cand-reason">{reason}</div>
</div>
""", unsafe_allow_html=True)

with col_detail:
    st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])
    for rank, item in enumerate(top_n, 1):
        writer.writerow([
            item["candidate_id"], rank, item["score"],
            make_reasoning(item["candidate"], item["matched"], item["has_prod"])
        ])

    st.download_button(
        "⬇️ Download submission.csv",
        buf.getvalue(),
        file_name="submission.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Score breakdown (rank 1)</div>',
                unsafe_allow_html=True)

    if top_n:
        best = top_n[0]
        c0   = best["candidate"]
        sk0, _ = score_skills(c0)
        exp0   = score_experience(c0)
        beh0   = score_behavioral(c0)
        car0,_ = score_career(c0)
        loc0   = score_location(c0)

        breakdown = {
            "Semantic / Skills": sk0,
            "Experience fit":    exp0,
            "Behavioral signals":beh0,
            "Career quality":    car0,
            "Location fit":      loc0,
        }
        for label, val in breakdown.items():
            bar_w = int(val * 100)
            color = "#7c6ff5" if val >= 0.7 else ("#facc15" if val >= 0.4 else "#f87171")
            st.markdown(f"""
<div style="margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;font-size:0.75rem;
              color:#8b8fa8;margin-bottom:3px">
    <span>{label}</span><span style="color:{color}">{val:.2f}</span>
  </div>
  <div style="background:#1a1d2e;border-radius:4px;height:6px;overflow:hidden">
    <div style="width:{bar_w}%;background:{color};height:6px;border-radius:4px"></div>
  </div>
</div>
""", unsafe_allow_html=True)
