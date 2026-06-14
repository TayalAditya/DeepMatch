# India Runs — Track 1: Intelligent Candidate Discovery

**Team:** India Runs  
**Challenge:** Redrob AI × Hack2Skill — Data & AI Challenge  
**Submission deadline:** 28 June 2026

---

## Reproduce the submission

```bash
pip install -r requirements.txt
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Runtime: ~75 seconds on CPU (16 GB RAM). No GPU required. No network access during ranking.

---

## Architecture

Three-stage hybrid ranker:

### Stage 1 — Fast structured pre-filter (100K → 5K, ~13s)
Every candidate gets a weighted composite of:
- **Skills match** — skill name matched against JD keywords, weighted by proficiency, duration credibility (log-scaled months), and endorsement trust
- **Experience years** — soft match on 5-9 year target range
- **Behavioral signals** — open_to_work, last active date, recruiter response rate, interview completion, GitHub activity, profile completeness
- **Career quality** — production deployment keywords in descriptions, tech industry fit, seniority in recent roles
- **Location** — India preference with bonus for Pune/Noida
- **Honeypot penalty** — detects impossible signal combinations and down-weights them

### Stage 2 — Semantic scoring (5K → scored, ~42s)
Encodes the JD and top-5K candidate profiles using `sentence-transformers/all-MiniLM-L6-v2` (CPU, batch=256). Cosine similarity gives a semantic fit score independent of keyword overlap.

### Stage 3 — Multi-signal combination (scored → top 100)
Final score = `0.35 × semantic + 0.28 × skills + 0.14 × career + 0.12 × behavioral + 0.06 × experience + 0.05 × location`  
Honeypot candidates receive up to 65% penalty on their final score.  
Sorted by rounded score descending; ties broken by `candidate_id` ascending per spec.

---

## Honeypot detection

Six heuristics flag suspicious profiles:
1. `years_of_experience` >> sum of career duration months
2. Multiple expert/advanced skills with 0 months used
3. Large skill list + near-zero platform assessment scores
4. All skills with identical non-zero endorsement counts
5. Perfect behavioural stats with zero platform activity
6. GitHub score = 100 with no verified contact or LinkedIn

---

## Compute constraints

| Constraint | Requirement | Actual |
|---|---|---|
| Runtime | < 5 min CPU | ~74s |
| RAM | ≤ 16 GB | ~3 GB peak |
| GPU | None | None used |
| Network during ranking | None | None |

---

## Files

| File | Description |
|---|---|
| `rank.py` | Main ranking script |
| `requirements.txt` | Python dependencies |
| `submission.csv` | Top-100 ranked candidates |
| `submission_metadata.yaml` | Team and compute metadata |
