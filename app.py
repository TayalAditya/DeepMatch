import streamlit as st
import json, csv, io, sys, os
from datetime import date, datetime

st.set_page_config(
    page_title="DeepMatch — Candidate Discovery",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ════════════════════════════════════════════════════════════════════════════
#  Styles
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --bg:#f6f7f9; --surface:#ffffff; --line:#e8eaed; --line-2:#dfe2e6;
  --ink:#13151a; --ink-2:#5b6472; --ink-3:#9099a6;
  --brand:#5b5bf0; --brand-soft:#eef0fe;
  --good:#0e9f6e; --good-soft:#e7f7f0;
  --warn:#c2710c; --warn-soft:#fdf3e6;
  --bad:#d23b56;  --bad-soft:#fdeef1;
}

html, body, [class*="css"]{ font-family:'Inter',system-ui,sans-serif; }
.stApp{ background:var(--bg); }
.block-container{ padding:1.4rem 2.4rem 3rem; max-width:1360px; }
#MainMenu, footer, header{ visibility:hidden; }

/* ── Brand header ────────────────────────────────────────── */
.hero{
  display:flex; align-items:center; justify-content:space-between;
  padding:0 0 1.2rem; margin-bottom:1.4rem; border-bottom:1px solid var(--line);
}
.hero-left{ display:flex; align-items:center; gap:.7rem; }
.hero-mark{
  width:34px; height:34px; border-radius:9px; display:grid; place-items:center;
  background:linear-gradient(135deg,#5b5bf0,#8b5cf6); color:#fff;
  font-weight:800; font-size:1rem; box-shadow:0 4px 12px rgba(91,91,240,.32);
}
.hero-name{ font-size:1.18rem; font-weight:800; color:var(--ink); letter-spacing:-.4px; line-height:1; }
.hero-tag{ font-size:.74rem; color:var(--ink-3); margin-top:3px; font-weight:500; }
.hero-job{
  text-align:right; font-size:.78rem; color:var(--ink-2); line-height:1.5;
}
.hero-job b{ color:var(--ink); font-weight:700; }

/* ── KPI strip ───────────────────────────────────────────── */
.kpis{ display:grid; grid-template-columns:repeat(5,1fr); gap:.8rem; margin-bottom:1.5rem; }
.kpi{
  background:var(--surface); border:1px solid var(--line); border-radius:13px;
  padding:.95rem 1.1rem; transition:transform .15s, box-shadow .15s;
}
.kpi:hover{ transform:translateY(-2px); box-shadow:0 8px 22px rgba(20,23,33,.06); }
.kpi .v{ font-size:1.55rem; font-weight:800; color:var(--ink); line-height:1; letter-spacing:-.5px; }
.kpi .l{ font-size:.72rem; color:var(--ink-3); margin-top:.45rem; font-weight:500; }
.kpi .l b{ color:var(--ink-2); }

/* ── Section label ───────────────────────────────────────── */
.sec{ font-size:.68rem; font-weight:700; color:var(--ink-3); letter-spacing:1.3px;
      text-transform:uppercase; margin:0 0 .65rem; }

/* ── Left list (navigator) ───────────────────────────────── */
/* the row IS a streamlit button, fully restyled */
div[data-testid="column"]:first-child .stButton > button{
  width:100%; text-align:left; background:var(--surface);
  border:1px solid var(--line); border-radius:12px; color:var(--ink);
  padding:.7rem .9rem; font-weight:600; font-size:.86rem; line-height:1.35;
  white-space:pre-line; transition:all .14s; margin-bottom:.05rem;
}
div[data-testid="column"]:first-child .stButton > button:hover{
  border-color:var(--brand); box-shadow:0 4px 14px rgba(91,91,240,.10);
  transform:translateX(2px);
}
/* selected row = primary button */
div[data-testid="column"]:first-child .stButton > button[kind="primary"]{
  background:var(--brand-soft); border-color:var(--brand);
  box-shadow:inset 3px 0 0 var(--brand); color:var(--ink);
}

/* ── Detail panel ────────────────────────────────────────── */
.panel{
  background:var(--surface); border:1px solid var(--line); border-radius:16px;
  padding:1.5rem 1.6rem; box-shadow:0 1px 3px rgba(20,23,33,.04);
}
.p-head{ display:flex; align-items:center; gap:1.1rem; margin-bottom:1.2rem; }
.avatar{
  width:54px; height:54px; border-radius:14px; flex:0 0 54px;
  display:grid; place-items:center; font-weight:800; font-size:1.25rem;
}
.p-name{ font-size:1.28rem; font-weight:800; color:var(--ink); letter-spacing:-.4px; line-height:1.15; }
.p-title{ font-size:.84rem; color:var(--ink-2); margin-top:3px; font-weight:500; }
.p-meta{ font-size:.76rem; color:var(--ink-3); margin-top:5px; }

/* score gauge */
.gauge{ width:78px; height:78px; border-radius:50%; flex:0 0 78px; display:grid; place-items:center; margin-left:auto; }
.gauge-in{ width:60px; height:60px; border-radius:50%; background:var(--surface);
           display:grid; place-items:center; text-align:center; }
.gauge-v{ font-size:1.15rem; font-weight:800; color:var(--ink); line-height:1; }
.gauge-l{ font-size:.55rem; font-weight:700; letter-spacing:.5px; text-transform:uppercase; margin-top:2px; }

/* verdict chip */
.verdict{ display:inline-flex; align-items:center; gap:6px; padding:5px 12px;
          border-radius:30px; font-size:.76rem; font-weight:700; }
.v-strong{ background:var(--good-soft); color:var(--good); }
.v-solid{  background:var(--brand-soft); color:var(--brand); }
.v-mod{    background:#eef1f5; color:var(--ink-2); }

/* why-callout */
.why{ background:linear-gradient(180deg,#fafbff,#f4f5fe); border:1px solid var(--line);
      border-radius:12px; padding:.85rem 1rem; font-size:.83rem; color:var(--ink);
      line-height:1.6; margin:1.1rem 0; }
.why b{ color:var(--brand); }

/* skill chips */
.chip{ display:inline-flex; align-items:center; gap:5px; border-radius:8px;
       padding:4px 10px; font-size:.74rem; font-weight:600; margin:3px 4px 3px 0; }
.chip-yes{ background:var(--good-soft); color:var(--good); }
.chip-gap{ background:#f3f4f6; color:var(--ink-3); border:1px dashed var(--line-2); }

/* score composition */
.bar-row{ margin-bottom:.7rem; }
.bar-top{ display:flex; justify-content:space-between; font-size:.77rem; margin-bottom:4px; }
.bar-top .nm{ color:var(--ink-2); font-weight:600; }
.bar-top .pc{ font-weight:700; }
.track{ height:7px; background:#eef0f3; border-radius:6px; overflow:hidden; }
.fill{ height:7px; border-radius:6px; }

/* signal grid */
.sg{ display:grid; grid-template-columns:1fr 1fr; gap:.55rem .9rem; }
.sg-item{ display:flex; align-items:center; gap:8px; font-size:.78rem; }
.dot{ width:8px; height:8px; border-radius:50%; flex:0 0 8px; }
.sg-k{ color:var(--ink-2); }
.sg-v{ color:var(--ink); font-weight:700; margin-left:auto; }

/* timeline */
.tl{ border-left:2px solid var(--line); padding-left:1rem; margin-left:4px; }
.tl-item{ position:relative; padding-bottom:.85rem; }
.tl-item:before{ content:''; position:absolute; left:-1.32rem; top:4px; width:9px; height:9px;
                 border-radius:50%; background:var(--brand); border:2px solid var(--surface); }
.tl-role{ font-size:.82rem; font-weight:700; color:var(--ink); }
.tl-co{ font-size:.76rem; color:var(--ink-2); }
.tl-when{ font-size:.71rem; color:var(--ink-3); margin-top:1px; }

.summary{ font-size:.82rem; color:var(--ink-2); line-height:1.7; }
.divider{ height:1px; background:var(--line); margin:1.2rem 0; }

/* dropzone */
.drop{ background:var(--surface); border:2px dashed var(--line-2); border-radius:16px;
       padding:3.2rem; text-align:center; margin-top:1rem; }
.drop .ic{ font-size:2.2rem; }
.drop .t{ font-weight:700; color:var(--ink); margin-top:.6rem; font-size:.95rem; }
.drop .s{ font-size:.8rem; color:var(--ink-3); margin-top:.35rem; }

/* generic streamlit buttons (export / run) live in non-first columns */
div[data-testid="column"]:not(:first-child) .stButton > button,
.stDownloadButton > button{
  background:var(--brand); color:#fff; border:none; border-radius:10px;
  padding:.55rem 1.3rem; font-weight:700; font-size:.83rem;
}
div[data-testid="column"]:not(:first-child) .stButton > button:hover,
.stDownloadButton > button:hover{ background:#4848d8; }
div[data-testid="column"]:not(:first-child) .stButton > button:disabled{
  background:#c9ccd6; color:#fff; }
.stCaption, .stCaption p{ color:var(--ink-3) !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
#  Header
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <div class="hero-left">
    <div class="hero-mark">◆</div>
    <div>
      <div class="hero-name">DeepMatch</div>
      <div class="hero-tag">Intelligent candidate discovery</div>
    </div>
  </div>
  <div class="hero-job">
    Ranking for <b>Senior AI Engineer</b><br>
    Redrob AI · Pune / Noida · 5–9 yrs
  </div>
</div>
""", unsafe_allow_html=True)

# ── Upload row ──────────────────────────────────────────────────────────────
uc, bc = st.columns([4, 1])
with uc:
    uploaded = st.file_uploader("Candidates file (JSONL)", type=["jsonl", "json"],
                                label_visibility="collapsed")
with bc:
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    run = st.button("Run ranking ◆", disabled=not uploaded, use_container_width=True)

if not uploaded:
    st.markdown("""
<div class="drop">
  <div class="ic">📂</div>
  <div class="t">Drop your candidates file to begin</div>
  <div class="s">JSONL or JSON — try <code>sample_candidates.json</code> from the hackathon bundle</div>
</div>""", unsafe_allow_html=True)
    st.stop()

# ── Load ────────────────────────────────────────────────────────────────────
raw = uploaded.read().decode("utf-8")
candidates = []
stripped = raw.strip()
try:
    parsed = json.loads(stripped)
    candidates = parsed if isinstance(parsed, list) else [parsed]
except Exception:
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            candidates.extend(obj) if isinstance(obj, list) else candidates.append(obj)
        except Exception:
            pass

st.caption(f"✓ {len(candidates)} candidates loaded from **{uploaded.name}**")

if not run:
    st.stop()

# ════════════════════════════════════════════════════════════════════════════
#  Rank
# ════════════════════════════════════════════════════════════════════════════
with st.spinner("Scoring candidates…"):
    sys.path.insert(0, os.path.dirname(__file__) or ".")
    from rank import (score_skills, score_experience, score_behavioral,
                      score_career, score_location, honeypot_penalty, make_reasoning)

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

        cand_skills_lower = {s.get("name","").lower() for s in c.get("skills",[])}
        missing = [m for m in JD_MUST
                   if not any(m.lower() in cs or cs in m.lower()
                              for cs in cand_skills_lower)][:5]

        results.append({
            "id": c["candidate_id"], "score": final,
            "matched": matched, "missing": missing,
            "has_prod": hprod, "hp": hp,
            "sk": sk, "exp": exp, "beh": beh, "car": car, "loc": loc,
            "candidate": c,
        })

    results.sort(key=lambda x: (-x["score"], x["id"]))
    top_n = results[:100]

# ════════════════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════════════════
AVATARS = [("#ede9fe","#6d28d9"),("#dbeafe","#1d4ed8"),("#dcfce7","#15803d"),
           ("#fef3c7","#b45309"),("#fae8ff","#a21caf"),("#cffafe","#0e7490"),
           ("#ffe4e6","#be123c"),("#e0e7ff","#4338ca")]

def avatar_colors(seed):
    return AVATARS[sum(ord(ch) for ch in str(seed)) % len(AVATARS)]

def cand_name(p):
    return p.get("anonymized_name") or p.get("current_title") or "Candidate"

def initials(name):
    parts = [w for w in name.split() if w]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper() if parts else "?"

def tier(sc):
    if sc >= 0.65: return ("Strong fit", "v-strong", "#0e9f6e")
    if sc >= 0.45: return ("Solid fit",  "v-solid",  "#5b5bf0")
    return ("Moderate fit", "v-mod", "#8a93a3")

def bar_color(v):
    return "#0e9f6e" if v >= 0.7 else ("#5b5bf0" if v >= 0.4 else "#aab2c0")

# ════════════════════════════════════════════════════════════════════════════
#  KPI strip
# ════════════════════════════════════════════════════════════════════════════
strong = sum(1 for r in top_n if r["score"] >= 0.65)
otw    = sum(1 for r in top_n if r["candidate"]["redrob_signals"].get("open_to_work_flag"))
hp_cnt = sum(1 for r in top_n if r["hp"] >= 0.5)
verified = len(top_n) - hp_cnt

st.markdown(f"""
<div class="kpis">
  <div class="kpi"><div class="v">{len(candidates):,}</div><div class="l">Candidates <b>scanned</b></div></div>
  <div class="kpi"><div class="v">{len(top_n)}</div><div class="l">Top <b>shortlist</b></div></div>
  <div class="kpi"><div class="v" style="color:#0e9f6e">{strong}</div><div class="l">Strong <b>matches</b></div></div>
  <div class="kpi"><div class="v">{otw}</div><div class="l">Open to <b>work</b></div></div>
  <div class="kpi"><div class="v" style="color:#0e9f6e">{verified}</div>
    <div class="l">Integrity <b>verified</b>{f" · {hp_cnt} to review" if hp_cnt else ""}</div></div>
</div>
""", unsafe_allow_html=True)

# ── Export ──────────────────────────────────────────────────────────────────
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["candidate_id","rank","score","reasoning"])
for rank_i, item in enumerate(top_n, 1):
    w.writerow([item["id"], rank_i, item["score"],
                make_reasoning(item["candidate"], item["matched"], item["has_prod"])])
dc, _ = st.columns([1, 5])
with dc:
    st.download_button("⬇  Export shortlist", buf.getvalue(),
                       file_name="submission.csv", mime="text/csv",
                       use_container_width=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
#  List  +  Detail  (reading-pane layout)
# ════════════════════════════════════════════════════════════════════════════
LIST_N   = min(len(top_n), 30)
selected = st.session_state.get("sel", 0)
selected = min(selected, len(top_n) - 1)

lcol, rcol = st.columns([4, 5], gap="large")

# ── Navigator ───────────────────────────────────────────────────────────────
with lcol:
    st.markdown(f'<div class="sec">Ranked candidates · top {LIST_N}</div>', unsafe_allow_html=True)
    for i, item in enumerate(top_n[:LIST_N]):
        p    = item["candidate"]["profile"]
        nm   = cand_name(p)
        ttl  = p.get("current_title", "—")
        sc   = item["score"]
        medal = {0:"🥇",1:"🥈",2:"🥉"}.get(i, f"#{i+1}")
        label = f"{medal}   {nm}  ·  {sc:.2f}\n{ttl} · {p.get('years_of_experience',0):.1f}y · {p.get('location','')}"
        if st.button(label, key=f"row_{i}", use_container_width=True,
                     type="primary" if i == selected else "secondary"):
            st.session_state["sel"] = i
            selected = i
            st.rerun()

# ── Detail panel ────────────────────────────────────────────────────────────
with rcol:
    st.markdown('<div class="sec">Candidate profile</div>', unsafe_allow_html=True)
    item = top_n[selected]
    c    = item["candidate"]
    p    = c["profile"]
    sig  = c["redrob_signals"]
    nm   = cand_name(p)
    sc   = item["score"]
    vlabel, vcls, vcol = tier(sc)
    bg, fg = avatar_colors(item["id"])
    deg = int(sc * 360)

    # header: avatar + name + gauge
    st.markdown(f"""
<div class="panel">
  <div class="p-head">
    <div class="avatar" style="background:{bg};color:{fg}">{initials(nm)}</div>
    <div>
      <div class="p-name">{nm}</div>
      <div class="p-title">{p.get('current_title','—')} · {p.get('current_company','')}</div>
      <div class="p-meta">{item['id']} · {p.get('years_of_experience',0):.1f} yrs · {p.get('location','')}, {p.get('country','')}</div>
    </div>
    <div class="gauge" style="background:conic-gradient({vcol} {deg}deg,#eceef2 0deg)">
      <div class="gauge-in">
        <div class="gauge-v">{sc:.2f}</div>
        <div class="gauge-l" style="color:{vcol}">rank #{selected+1}</div>
      </div>
    </div>
  </div>
  <span class="verdict {vcls}">● {vlabel}</span>
""", unsafe_allow_html=True)

    # why ranked here — positive narrative
    dims = {"skills match": item["sk"], "experience fit": item["exp"],
            "platform engagement": item["beh"], "career quality": item["car"]}
    top_dim = max(dims, key=dims.get)
    n_match = len(item["matched"] or [])
    bits = [f"Leads on <b>{top_dim}</b> ({dims[top_dim]:.0%})"]
    if n_match:
        bits.append(f"brings <b>{n_match}</b> of the must-have stack ({', '.join((item['matched'] or [])[:3])})")
    if item["has_prod"]:
        bits.append("shows <b>production deployment</b> experience")
    if sig.get("open_to_work_flag"):
        bits.append("is <b>open to work</b>")
    why = " · ".join(bits) + "."
    st.markdown(f'<div class="why">{why}</div>', unsafe_allow_html=True)

    # strengths
    st.markdown('<div class="sec" style="margin-top:.2rem">Matched strengths</div>', unsafe_allow_html=True)
    if item["matched"]:
        st.markdown("".join(f'<span class="chip chip-yes">✓ {s}</span>'
                            for s in item["matched"]), unsafe_allow_html=True)
    else:
        st.markdown('<span style="font-size:.8rem;color:var(--ink-3)">Matched on semantic profile fit rather than exact keywords.</span>',
                    unsafe_allow_html=True)
    if item["missing"]:
        st.markdown('<div style="margin-top:.7rem;font-size:.72rem;color:var(--ink-3);font-weight:600">Not listed yet</div>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="chip chip-gap">{s}</span>'
                            for s in item["missing"]), unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # score composition
    st.markdown('<div class="sec">Score composition</div>', unsafe_allow_html=True)
    comp = [("Skills match", item["sk"]), ("Experience fit", item["exp"]),
            ("Platform engagement", item["beh"]), ("Career quality", item["car"]),
            ("Location fit", item["loc"])]
    bars = ""
    for label, val in comp:
        col = bar_color(val)
        bars += f"""<div class="bar-row">
  <div class="bar-top"><span class="nm">{label}</span><span class="pc" style="color:{col}">{val:.0%}</span></div>
  <div class="track"><div class="fill" style="width:{int(val*100)}%;background:{col}"></div></div>
</div>"""
    st.markdown(bars, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # signals grid
    st.markdown('<div class="sec">Platform signals</div>', unsafe_allow_html=True)
    def dot(good):  # green / amber / neutral
        return "#0e9f6e" if good is True else ("#c2710c" if good is False else "#c2c7d0")
    rr = sig.get("recruiter_response_rate", 0)
    gh = sig.get("github_activity_score", -1)
    ic = sig.get("interview_completion_rate", 0)
    np_ = sig.get("notice_period_days", 0)
    pc = sig.get("profile_completeness_score", 0)
    sg_rows = [
        ("Open to work", "Yes" if sig.get("open_to_work_flag") else "No", sig.get("open_to_work_flag")),
        ("Recruiter response", f"{rr:.0%}", rr >= 0.6 if rr else None),
        ("Interview completion", f"{ic:.0%}", ic >= 0.7 if ic else None),
        ("Notice period", f"{np_}d", np_ <= 60 if np_ else None),
        ("GitHub activity", f"{gh:.0f}/100" if gh >= 0 else "—", (gh >= 50) if gh >= 0 else None),
        ("Profile complete", f"{pc:.0f}%", pc >= 75 if pc else None),
    ]
    sg = '<div class="sg">'
    for k, v, good in sg_rows:
        sg += f'<div class="sg-item"><span class="dot" style="background:{dot(good)}"></span><span class="sg-k">{k}</span><span class="sg-v">{v}</span></div>'
    sg += '</div>'
    st.markdown(sg, unsafe_allow_html=True)

    # honeypot note — only when genuinely flagged
    if item["hp"] >= 0.5:
        st.markdown(f"""<div style="margin-top:.9rem;background:var(--bad-soft);border:1px solid #f6cdd6;
          border-radius:10px;padding:.7rem .9rem;font-size:.78rem;color:var(--bad);font-weight:600">
          ⚠ Integrity check: this profile shows inconsistent signals worth a manual review before outreach.</div>""",
          unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # career timeline
    hist = c.get("career_history", [])[:3]
    if hist:
        st.markdown('<div class="sec">Recent experience</div>', unsafe_allow_html=True)
        tl = '<div class="tl">'
        for h in hist:
            when = f"{(h.get('start_date') or '')[:4]} – {'Present' if h.get('is_current') else (h.get('end_date') or '')[:4]}"
            mo = h.get("duration_months", 0)
            tl += f"""<div class="tl-item">
  <div class="tl-role">{h.get('title','—')}</div>
  <div class="tl-co">{h.get('company','')} · {h.get('industry','')}</div>
  <div class="tl-when">{when} · {mo} mo</div>
</div>"""
        tl += '</div>'
        st.markdown(tl, unsafe_allow_html=True)

    # summary
    summ = p.get("summary", "")
    if summ:
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec">Summary</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary">{summ[:420]}{"…" if len(summ) > 420 else ""}</div>',
                    unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .panel
