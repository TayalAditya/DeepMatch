import streamlit as st
import json, csv, io, sys, os

st.set_page_config(page_title="DeepMatch — Candidate Ranker", page_icon="🎯")
st.title("🎯 DeepMatch — Intelligent Candidate Ranker")
st.caption("India Runs Hackathon · Track 1 · Team DeepMatch")

st.markdown("""
Upload a JSONL file of candidates (one JSON object per line) and get a ranked shortlist
for the **Senior AI Engineer** role at Redrob AI.

> Works on small samples (≤ 500 candidates) within the browser. Full 100K run takes ~74s on CPU.
""")

uploaded = st.file_uploader("Upload candidates.jsonl", type=["jsonl", "json"])

if uploaded:
    raw = uploaded.read().decode("utf-8")
    candidates = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if line:
            try:
                candidates.append(json.loads(line))
            except Exception:
                pass

    st.info(f"Loaded **{len(candidates)}** candidates")

    if st.button("🚀 Run Ranker", type="primary"):
        with st.spinner("Ranking candidates..."):
            # Import ranker functions
            sys.path.insert(0, os.path.dirname(__file__))
            from rank import fast_structured_score, score_skills, score_experience
            from rank import score_behavioral, score_career, score_location
            from rank import honeypot_penalty, make_reasoning

            results = []
            for c in candidates:
                sk, matched = score_skills(c)
                exp = score_experience(c)
                beh = score_behavioral(c)
                car, has_prod = score_career(c)
                loc = score_location(c)
                hp  = honeypot_penalty(c)

                raw = (0.35 * sk + 0.20 * exp + 0.20 * beh +
                       0.15 * car + 0.10 * loc)
                final = raw * (1.0 - 0.65 * hp)

                results.append({
                    "candidate_id": c["candidate_id"],
                    "score": round(final, 4),
                    "matched": matched,
                    "has_prod": has_prod,
                    "candidate": c,
                })

            results.sort(key=lambda x: (-x["score"], x["candidate_id"]))
            top_n = results[:100]

        st.success(f"Done! Top {len(top_n)} candidates ranked.")

        # Display table
        import pandas as pd
        rows = []
        for rank, item in enumerate(top_n, 1):
            p = item["candidate"]["profile"]
            rows.append({
                "Rank": rank,
                "ID": item["candidate_id"],
                "Title": p.get("current_title", ""),
                "Yrs Exp": p.get("years_of_experience", 0),
                "Location": p.get("location", ""),
                "Score": item["score"],
                "Reasoning": make_reasoning(item["candidate"], item["matched"], item["has_prod"])
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Download CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, item in enumerate(top_n, 1):
            writer.writerow([
                item["candidate_id"], rank, item["score"],
                make_reasoning(item["candidate"], item["matched"], item["has_prod"])
            ])
        st.download_button("⬇️ Download submission.csv", buf.getvalue(),
                           file_name="submission.csv", mime="text/csv")
else:
    st.info("👆 Upload a candidates JSONL file to get started. You can use `sample_candidates.json` from the hackathon bundle.")
