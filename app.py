import streamlit as st
import json, csv, io, sys, os, math
from datetime import date, datetime

st.set_page_config(
    page_title="DeepMatch",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Reset & base ───────────────────────── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding: 2rem 3rem; max-width: 1280px; }
.stApp { background: #f7f8fa; }

/* ── Top nav bar ────────────────────────── */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    background: #ffffff; border-bottom: 1px solid #e5e7eb;
    padding: 0.9rem 0; margin-bottom: 2rem;
}
.topbar-brand { font-size: 1.25rem; font-weight: 800; color: #111827; letter-spacing: -0.3px; }
.topbar-role  { font-size: 0.82rem; color: #6b7280; background: #f3f4f6;
                padding: 4px 12px; border-radius: 20px; }

/* ── Section headings ───────────────────── */
.sec-title { font-size: 0.7rem; font-weight: 700; color: #9ca3af;
             letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 0.75rem; }

/* ── Stat chips ─────────────────────────── */
.stats-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.stat-chip {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 0.85rem 1.2rem; min-width: 130px;
}
.stat-chip .val  { font-size: 1.6rem; font-weight: 700; color: #111827; line-height: 1; }
.stat-chip .lbl  { font-size: 0.72rem; color: #9ca3af; margin-top: 3px; }

/* ── Candidate card ─────────────────────── */
.ccard {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 1.1rem 1.3rem; margin-bottom: 0.7rem; cursor: pointer;
    transition: box-shadow 0.15s, border-color 0.15s;
}
.ccard:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.07); border-color: #d1d5db; }
.ccard-top   { display: flex; justify-content: space-between; align-items: flex-start; }
.ccard-rank  { font-size: 0.68rem; font-weight: 600; color: #9ca3af; margin-bottom: 3px; }
.ccard-title { font-size: 0.97rem; font-weight: 700; color: #111827; }
.ccard-meta  { font-size: 0.77rem; color: #6b7280; margin-top: 2px; }
.ccard-footer{ margin-top: 0.65rem; display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }

/* ── Match score badge ───────────────────── */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 5px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 600;
}
.badge-strong { background: #dcfce7; color: #15803d; }
.badge-good   { background: #fef9c3; color: #a16207; }
.badge-fair   { background: #fee2e2; color: #b91c1c; }

/* ── Skill chip ─────────────────────────── */
.sk-match { display:inline-block; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe;
            border-radius:5px; padding:2px 8px; font-size:0.7rem; margin:2px 3px 2px 0; }
.sk-miss  { display:inline-block; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca;
            border-radius:5px; padding:2px 8px; font-size:0.7rem; margin:2px 3px 2px 0; }

/* ── Signal pill ────────────────────────── */
.sig-ok   { display:inline-block; background:#f0fdf4; color:#166534; border-radius:5px;
            padding:2px 8px; font-size:0.7rem; margin:2px 3px 2px 0; }
.sig-warn { display:inline-block; background:#fff7ed; color:#9a3412; border-radius:5px;
            padding:2px 8px; font-size:0.7rem; margin:2px 3px 2px 0; }
.sig-neu  { display:inline-block; background:#f9fafb; color:#374151; border:1px solid #e5e7eb;
            border-radius:5px; padding:2px 8px; font-size:0.7rem; margin:2px 3px 2px 0; }

/* ── Detail panel ───────────────────────── */
.detail-panel {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 1.4rem; height: fit-content;
}
.detail-name  { font-size: 1.1rem; font-weight: 700; color: #111827; margin-bottom: 2px; }
.detail-sub   { font-size: 0.82rem; color: #6b7280; margin-bottom: 1rem; }
.mini-bar-bg  { background: #f3f4f6; border-radius: 4px; height: 7px; overflow:hidden; margin-top:3px; }
.bar-label    { display:flex; justify-content:space-between;
                font-size:0.72rem; color:#6b7280; margin-bottom:1px; }

/* ── Upload area ────────────────────────── */
.upload-placeholder {
    background: #ffffff; border: 2px dashed #d1d5db; border-radius: 12px;
    padding: 3rem; text-align: center; color: #6b7280; margin-top: 1rem;
}

/* ── Streamlit overrides ────────────────── */
div[data-testid="stFileUploader"] label { font-size: 0.82rem; color: #374151; }
.stButton > button {
    background: #111827; color: #f9fafb; border: none;
    border-radius: 8px; padding: 0.5rem 1.5rem; font-weight: 600;
}
.stButton > button:hover { background: #1f2937; }
button[kind="secondary"] { background: #f3f4f6 !important; color: #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ── Nav ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <span class="topbar-brand">🎯 DeepMatch</span>
  <span class="topbar-role">Senior AI Engineer · Redrob AI · Pune/Noida · 5–9 yrs</span>
</div>
""", unsafe_allow_html=True)

# ── Upload row ────────────────────────────────────────────────────────────────
uc, bc = st.columns([4, 1])
with uc:
    uploaded = st.file_uploader("Candidates file (JSONL)", type=["jsonl", "json"],
                                label_visibility="collapsed")
with bc:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("Run ranking", disabled=not uploaded, use_container_width=True)

if not uploaded:
    st.markdown("""
<div class="upload-placeholder">
  <div style="font-size:2rem">📂</div>
  <div style="font-weight:600; color:#374151; margin-top:0.5rem">
      Drop your candidates JSONL here
  </div>
  <div style="font-size:0.8rem; margin-top:0.3rem">
      Use <code>sample_candidates.json</code> from the hackathon bundle to try
  </div>
</div>""", unsafe_allow_html=True)
    st.stop()

# ── Load ──────────────────────────────────────────────────────────────────────
raw = uploaded.read().decode("utf-8")
candidates = []
for line in raw.strip().splitlines():
    line = line.strip()
    if line:
        try:
            obj = json.loads(line)
            if isinstance(obj, list):
                candidates.extend(obj)
            else:
                candidates.append(obj)
        except Exception:
            pass

st.caption(f"{len(candidates)} candidates loaded from **{uploaded.name}**")

if not run:
    st.stop()

# ── Rank ──────────────────────────────────────────────────────────────────────
with st.spinner("Ranking…"):
    sys.path.insert(0, os.path.dirname(__file__) or ".")
    from rank import (score_skills, score_experience, score_behavioral,
                      score_career, score_location, honeypot_penalty, make_reasoning,
                      SKILL_WEIGHTS)

    JD_MUST = ["FAISS","Vector Search","Embeddings","Sentence Transformers",
               "Elasticsearch","OpenSearch","Pinecone","Weaviate","Qdrant",
               "Semantic Search","RAG","NDCG","MRR","Learning to Rank",
               "Hybrid Search","Dense Retrieval"]

    results = []
    for c in candidates:
        sk, matched = score_skills(c)
        exp         = score_experience(c)
        beh         = score_behavioral(c)
        car, hprod  = score_career(c)
        loc         = score_location(c)
        hp          = honeypot_penalty(c)

        raw_sc = 0.35*sk + 0.20*exp + 0.20*beh + 0.15*car + 0.10*loc
        final  = round(raw_sc * (1.0 - 0.65*hp), 4)

        # which JD must-haves are missing
        cand_skills_lower = {s.get("name","").lower() for s in c.get("skills",[])}
        missing = [m for m in JD_MUST
                   if not any(m.lower() in cs or cs in m.lower()
                              for cs in cand_skills_lower)][:4]

        results.append({
            "id": c["candidate_id"], "score": final,
            "matched": matched, "missing": missing,
            "has_prod": hprod, "hp": hp,
            "sk": sk, "exp": exp, "beh": beh, "car": car, "loc": loc,
            "candidate": c,
        })

    results.sort(key=lambda x: (-x["score"], x["id"]))
    top_n = results[:100]

# ── Stats row ─────────────────────────────────────────────────────────────────
strong = sum(1 for r in top_n if r["score"] >= 0.65)
otw    = sum(1 for r in top_n if r["candidate"]["redrob_signals"].get("open_to_work_flag"))
hp_cnt = sum(1 for r in top_n if r["hp"] >= 0.5)

st.markdown(f"""
<div class="stats-row">
  <div class="stat-chip"><div class="val">{len(candidates)}</div><div class="lbl">Candidates scanned</div></div>
  <div class="stat-chip"><div class="val">{len(top_n)}</div><div class="lbl">Shortlisted</div></div>
  <div class="stat-chip"><div class="val">{strong}</div><div class="lbl">Strong match (≥0.65)</div></div>
  <div class="stat-chip"><div class="val">{otw}</div><div class="lbl">Open to work</div></div>
  <div class="stat-chip"><div class="val" style="color:{'#dc2626' if hp_cnt else '#15803d'}">{hp_cnt}</div>
    <div class="lbl">Honeypots flagged</div></div>
  <div class="stat-chip"><div class="val">{top_n[0]['score']:.2f}</div><div class="lbl">Top match score</div></div>
</div>
""", unsafe_allow_html=True)

# ── Download button ───────────────────────────────────────────────────────────
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["candidate_id","rank","score","reasoning"])
for rank, item in enumerate(top_n, 1):
    w.writerow([item["id"], rank, item["score"],
                make_reasoning(item["candidate"], item["matched"], item["has_prod"])])

dc, _ = st.columns([1, 5])
with dc:
    st.download_button("⬇ Export CSV", buf.getvalue(),
                       file_name="submission.csv", mime="text/csv",
                       use_container_width=True)

st.markdown("---")

# ── Main layout: list + detail panel ─────────────────────────────────────────
LIST_N = min(len(top_n), 30)   # show top 30 in list
selected = st.session_state.get("selected_idx", 0)

lcol, rcol = st.columns([5, 3], gap="large")

with lcol:
    st.markdown('<div class="sec-title">Ranked candidates</div>', unsafe_allow_html=True)

    for i, item in enumerate(top_n[:LIST_N]):
        p   = item["candidate"]["profile"]
        sig = item["candidate"]["redrob_signals"]
        sc  = item["score"]

        # badge
        if sc >= 0.65:
            badge = '<span class="badge badge-strong">● Strong match</span>'
        elif sc >= 0.45:
            badge = '<span class="badge badge-good">● Good match</span>'
        else:
            badge = '<span class="badge badge-fair">● Fair match</span>'

        # matched skills chips
        sk_html = "".join(f'<span class="sk-match">{s}</span>'
                          for s in (item["matched"] or [])[:4])

        # signal pills
        pills = ""
        if sig.get("open_to_work_flag"):
            pills += '<span class="sig-ok">Open to work</span>'
        else:
            pills += '<span class="sig-warn">Not open</span>'

        rr = sig.get("recruiter_response_rate", 0)
        if rr >= 0.7:
            pills += f'<span class="sig-ok">{rr:.0%} response</span>'
        elif rr < 0.3:
            pills += f'<span class="sig-warn">{rr:.0%} response</span>'

        gh = sig.get("github_activity_score", -1)
        if gh >= 60:
            pills += f'<span class="sig-ok">GitHub {gh:.0f}/100</span>'
        elif gh == -1:
            pills += '<span class="sig-neu">No GitHub</span>'

        notice = sig.get("notice_period_days", 0)
        if notice > 0:
            pills += f'<span class="sig-neu">{notice}d notice</span>'

        loc_str = f"{p.get('location','')}, {p.get('country','')}"

        # click to select
        if st.button(f"#{i+1}  {p.get('current_title','?')}  ·  {sc:.3f}",
                     key=f"btn_{i}",
                     use_container_width=True,
                     type="secondary"):
            st.session_state["selected_idx"] = i
            selected = i

        st.markdown(f"""
<div class="ccard" style="margin-top:-0.4rem">
  <div class="ccard-top">
    <div>
      <div class="ccard-rank">{item['id']}</div>
      <div class="ccard-meta">
        {p.get('years_of_experience',0):.1f} yrs exp &nbsp;·&nbsp; {loc_str}
      </div>
    </div>
    {badge}
  </div>
  <div class="ccard-footer">{sk_html}</div>
  <div class="ccard-footer">{pills}</div>
</div>
""", unsafe_allow_html=True)

with rcol:
    st.markdown('<div class="sec-title">Candidate profile</div>', unsafe_allow_html=True)

    if top_n:
        idx = min(selected, len(top_n)-1)
        item = top_n[idx]
        c    = item["candidate"]
        p    = c["profile"]
        sig  = c["redrob_signals"]

        st.markdown(f"""
<div class="detail-panel">
  <div class="detail-name">{p.get('current_title','?')}</div>
  <div class="detail-sub">
    {item['id']} &nbsp;·&nbsp;
    {p.get('years_of_experience',0):.1f} yrs &nbsp;·&nbsp;
    {p.get('location','')}, {p.get('country','')}
  </div>
""", unsafe_allow_html=True)

        # Score breakdown bars
        breakdown = [
            ("Skills match",     item["sk"]),
            ("Experience fit",   item["exp"]),
            ("Platform signals", item["beh"]),
            ("Career quality",   item["car"]),
            ("Location fit",     item["loc"]),
        ]
        for label, val in breakdown:
            bar_w = int(val * 100)
            color = "#16a34a" if val >= 0.7 else ("#d97706" if val >= 0.4 else "#dc2626")
            st.markdown(f"""
<div style="margin-bottom:10px">
  <div class="bar-label"><span>{label}</span><span style="color:{color};font-weight:600">{val:.0%}</span></div>
  <div class="mini-bar-bg">
    <div style="width:{bar_w}%;background:{color};height:7px;border-radius:4px"></div>
  </div>
</div>""", unsafe_allow_html=True)

        # Matched vs missing skills
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-title">Skills</div>', unsafe_allow_html=True)

        matched_html = "".join(
            f'<span class="sk-match">✓ {s}</span>' for s in (item["matched"] or []))
        missing_html = "".join(
            f'<span class="sk-miss">✗ {s}</span>' for s in (item["missing"] or []))
        st.markdown(matched_html + missing_html, unsafe_allow_html=True)

        # Key signals
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-title">Signals</div>', unsafe_allow_html=True)

        sig_items = []
        sig_items.append(("Open to work", sig.get("open_to_work_flag",False), True))
        sig_items.append((f"Response rate {sig.get('recruiter_response_rate',0):.0%}",
                          sig.get("recruiter_response_rate",0) >= 0.6, False))
        gh = sig.get("github_activity_score",-1)
        if gh >= 0:
            sig_items.append((f"GitHub {gh:.0f}/100", gh >= 50, False))
        sig_items.append((f"Interview completion {sig.get('interview_completion_rate',0):.0%}",
                          sig.get("interview_completion_rate",0) >= 0.7, False))
        sig_items.append((f"Notice {sig.get('notice_period_days',0)}d",
                          sig.get("notice_period_days",0) <= 60, False))

        sig_html = ""
        for label, good, _ in sig_items:
            cls = "sig-ok" if good else "sig-warn"
            sig_html += f'<span class="{cls}">{label}</span>'
        st.markdown(sig_html, unsafe_allow_html=True)

        # Summary snippet
        summary = p.get("summary","")
        if summary:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-title">Summary</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.8rem;color:#374151;line-height:1.6">'
                        f'{summary[:400]}{"…" if len(summary)>400 else ""}</div>',
                        unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
