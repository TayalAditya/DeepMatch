#!/usr/bin/env python3
"""
rank.py — Intelligent Candidate Discovery & Ranking
India Runs Hackathon — Track 1: Data & AI Challenge

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Architecture:
    Stage 1: Fast structured pre-filter   (100K → top 5K,  ~25s CPU)
    Stage 2: Semantic scoring              (top 5K → top 500, ~35s CPU)
    Stage 3: Multi-signal combination      (top 500 → top 100)
"""

import json
import csv
import argparse
import time
import math
import os
import sys
from datetime import datetime, date
from typing import List, Dict, Tuple

import numpy as np

# =========================================================================
# JD CONFIGURATION  (Senior AI Engineer — Redrob AI, Pune/Noida, 5-9 yrs)
# =========================================================================

JD_TEXT = """
Senior AI Engineer, Founding Team at Redrob AI.
Redrob AI is a Series A AI-native talent intelligence platform.
Location: Pune or Noida, India (Hybrid). Open to relocation from Tier-1 Indian cities.
Required experience: 5 to 9 years.

Role: Own the intelligence layer — the ranking, retrieval, and matching systems
that decide what recruiters see when they search for candidates.

First 90 days: audit existing BM25 rule-based system, ship v2 ranking system with
embeddings and hybrid retrieval, set up evaluation infrastructure for offline
benchmarks, online A/B testing, recruiter feedback loops.

MUST HAVE:
Production experience with embeddings-based retrieval systems:
sentence-transformers, OpenAI embeddings, BGE, E5, or similar.
Must have handled embedding drift, index refresh, retrieval-quality regression
in a live production environment with real users.

Production experience with vector databases or hybrid search infrastructure:
Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS.
The specific technology does not matter; operational production experience does.

Strong Python. Code quality and production mindset matter.

Hands-on experience designing evaluation frameworks for ranking systems:
NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation.

PREFERRED:
LLM fine-tuning: LoRA, QLoRA, PEFT.
Learning-to-rank models: XGBoost-based or neural LTR.
Prior exposure to HR-tech, recruiting technology, or marketplace products.
Background in distributed systems or large-scale inference optimization.
Open-source contributions in AI/ML.
GitHub activity demonstrating active coding.

DISQUALIFIERS:
Pure research environment without any production deployment.
AI experience only from recent LangChain/OpenAI wrapper projects under 12 months.
Senior engineer who has not written production code in the last 18 months.
"""

# Skill name → importance weight (higher = more critical for the JD)
SKILL_WEIGHTS: Dict[str, float] = {
    # Core retrieval (must-have tier)
    "faiss": 3.0, "vector search": 3.0, "vector database": 3.0, "vector db": 3.0,
    "embeddings": 2.8, "dense retrieval": 2.8, "semantic search": 2.8,
    "sentence-transformers": 2.8, "sentence transformers": 2.8,
    "hybrid search": 2.8, "rag": 2.8, "retrieval augmented generation": 2.8,
    "retrieval augmented": 2.8,
    # Vector DB tools
    "pinecone": 2.6, "weaviate": 2.6, "qdrant": 2.6, "milvus": 2.6,
    "opensearch": 2.5, "elasticsearch": 2.5, "bge": 2.5, "e5": 2.3,
    # Ranking / evaluation (must-have tier)
    "ranking": 2.5, "learning-to-rank": 2.5, "learning to rank": 2.5,
    "ndcg": 3.0, "mrr": 3.0, "map": 2.5, "bm25": 2.2,
    "reranking": 2.5, "re-ranking": 2.5, "information retrieval": 2.5,
    "recommendation system": 2.2, "recommendation": 2.0, "search": 1.8,
    # LLM / ML
    "llm": 2.0, "large language model": 2.0, "fine-tuning": 2.0,
    "fine tuning": 2.0, "lora": 2.0, "qlora": 2.0, "peft": 2.0,
    "transformers": 2.0, "bert": 1.8, "nlp": 1.8,
    "natural language processing": 1.8,
    # Core engineering
    "python": 2.0, "pytorch": 1.8, "tensorflow": 1.4,
    # Infra / evaluation
    "a/b testing": 2.0, "distributed systems": 1.5, "mlops": 1.8,
    "xgboost": 1.5, "open source": 1.5, "open-source": 1.5,
    # HR / marketplace
    "talent": 1.5, "recruiting": 1.5, "hr tech": 1.5, "hr-tech": 1.5,
    "job matching": 2.0, "candidate matching": 2.0, "matching": 1.8,
    "marketplace": 1.5,
}

# Words in career descriptions that signal real production deployment
PROD_KEYWORDS = [
    "deployed", "production", "shipped", "launched", "real users", "live system",
    "at scale", "million", "billion", "latency", "throughput", "ranking system",
    "retrieval system", "search system", "recommendation", "embedding", "vector",
    "faiss", "elasticsearch", "opensearch", "pinecone", "weaviate", "qdrant",
    "a/b test", "index refresh", "recall@", "precision@", "offline eval",
]

REF_DATE = date(2026, 6, 14)


# =========================================================================
# HONEYPOT DETECTION
# =========================================================================

def honeypot_penalty(c: Dict) -> float:
    """
    Return 0.0 (clean) → 1.0 (very likely honeypot).
    The dataset contains ~80 profiles with subtly impossible signal combinations.
    We penalise rather than hard-discard so genuine edge cases are not harmed.
    """
    pen = 0.0
    profile = c.get("profile", {})
    career  = c.get("career_history", [])
    skills  = c.get("skills", [])
    signals = c.get("redrob_signals", {})
    yoe     = profile.get("years_of_experience", 0)

    # 1. Claimed years_of_experience >> sum of career duration months
    total_months = sum(r.get("duration_months", 0) for r in career)
    if total_months > 0 and yoe > (total_months / 12) * 1.8:
        pen += 0.50

    # 2. Multiple "expert"/"advanced" skills with 0 months of use
    expert_zero = sum(
        1 for s in skills
        if s.get("proficiency") in ("expert", "advanced")
        and s.get("duration_months", 1) == 0
    )
    if expert_zero >= 3:
        pen += 0.40

    # 3. Large skill list + near-zero platform assessment scores
    assessments = signals.get("skill_assessment_scores", {})
    if assessments:
        avg_score = sum(assessments.values()) / len(assessments)
        if len(skills) > 12 and avg_score < 25:
            pen += 0.35

    # 4. Every skill has an identical non-zero endorsement count (synthetic stuffing)
    endorse_vals = [s.get("endorsements", 0) for s in skills if s.get("endorsements", 0) > 0]
    if len(endorse_vals) >= 5 and len(set(endorse_vals)) == 1:
        pen += 0.25

    # 5. Perfect behavioural stats with zero platform activity
    if (
        signals.get("offer_acceptance_rate", -1) == 1.0
        and signals.get("interview_completion_rate", 0) == 1.0
        and signals.get("applications_submitted_30d", 0) == 0
    ):
        pen += 0.20

    # 6. GitHub score = 100 but no verified contact and no LinkedIn
    if (
        signals.get("github_activity_score", 0) == 100
        and not signals.get("linkedin_connected", False)
        and not signals.get("verified_email", False)
    ):
        pen += 0.20

    return min(pen, 1.0)


# =========================================================================
# INDIVIDUAL SCORING SIGNALS
# =========================================================================

def score_skills(c: Dict) -> Tuple[float, List[str]]:
    """
    Multi-factor skill match:
      proficiency  ×  duration credibility  ×  endorsement trust
    Returns (normalised_score ∈ [0,1], list_of_matched_skill_names).
    """
    skills      = c.get("skills", [])
    assessments = c.get("redrob_signals", {}).get("skill_assessment_scores", {})

    prof_mult = {"beginner": 0.35, "intermediate": 0.65, "advanced": 0.88, "expert": 1.0}
    max_possible = sum(sorted(SKILL_WEIGHTS.values(), reverse=True)[:10])

    total   = 0.0
    matched = []

    for sk in skills:
        name  = sk.get("name", "").lower().strip()
        prof  = sk.get("proficiency", "intermediate")
        endorse = sk.get("endorsements", 0)
        dur   = sk.get("duration_months", 0)

        best_w, best_label = 0.0, None
        for key, w in SKILL_WEIGHTS.items():
            if key in name or name in key or (len(name) > 4 and name in key):
                if w > best_w:
                    best_w, best_label = w, sk.get("name", key)

        if best_w > 0:
            pm = prof_mult.get(prof, 0.65)
            dm = min(1.0, dur / 36.0) if dur > 0 else 0.40          # duration credibility
            em = min(1.0, math.log1p(endorse) / math.log1p(60))       # endorsement trust

            # Bonus if there's a platform assessment that matches this skill
            ab = 0.0
            for ak, av in assessments.items():
                if ak.lower() in name or name in ak.lower():
                    ab = (av / 100.0) * 0.15
                    break

            total += best_w * pm * (0.45 * dm + 0.35 * em + 0.20) + ab
            matched.append(best_label)

    return min(1.0, total / max_possible), matched[:6]


def score_experience(c: Dict) -> float:
    """Soft match on years_of_experience against JD target 5-9 years."""
    yoe = c.get("profile", {}).get("years_of_experience", 0)
    if 5 <= yoe <= 9:       return 1.00
    if 4 <= yoe < 5:        return 0.85
    if 9 < yoe <= 11:       return 0.85
    if 3 <= yoe < 4:        return 0.65
    if 11 < yoe <= 13:      return 0.65
    if 2 <= yoe < 3:        return 0.40
    if 13 < yoe <= 16:      return 0.55   # overqualified but usable
    return 0.20


def score_behavioral(c: Dict) -> float:
    """Weighted aggregate of 23 Redrob platform signals."""
    s = c.get("redrob_signals", {})
    score = 0.0

    # Open-to-work (most decisive availability signal)
    if s.get("open_to_work_flag", False):
        score += 0.25

    # Recency of last login
    try:
        last = datetime.strptime(s.get("last_active_date", "2020-01-01"), "%Y-%m-%d").date()
        days = (REF_DATE - last).days
        rec  = (1.0 if days <= 7 else 0.8 if days <= 30 else
                0.5 if days <= 90 else 0.2 if days <= 365 else 0.05)
    except Exception:
        rec = 0.30
    score += 0.18 * rec

    # Recruiter response rate
    score += 0.15 * s.get("recruiter_response_rate", 0.5)

    # Interview completion rate
    score += 0.10 * s.get("interview_completion_rate", 0.5)

    # GitHub activity (−1 means not linked)
    gh = s.get("github_activity_score", -1)
    score += 0.15 * (gh / 100.0 if gh >= 0 else 0.15)

    # Profile completeness
    score += 0.10 * (s.get("profile_completeness_score", 50) / 100.0)

    # Recruiter saves in last 30 days (social proof)
    saved = min(1.0, s.get("saved_by_recruiters_30d", 0) / 8.0)
    score += 0.07 * saved

    return score


def score_career(c: Dict) -> Tuple[float, bool]:
    """
    Career quality: production evidence, industry relevance, seniority progression.
    Returns (score, has_production_evidence).
    """
    career = c.get("career_history", [])
    if not career:
        return 0.25, False

    prod_hits = sum(
        1 for job in career
        if any(kw in job.get("description", "").lower() for kw in PROD_KEYWORDS)
    )
    production_score = min(1.0, prod_hits / max(len(career), 1))

    tech_industries = {
        "technology", "software", "ai", "machine learning", "data",
        "saas", "fintech", "edtech", "e-commerce", "internet", "startup", "platform"
    }
    tech_count = sum(
        1 for j in career
        if any(t in j.get("industry", "").lower() for t in tech_industries)
    )
    industry_score = tech_count / len(career)

    senior_words = {"senior", "lead", "principal", "staff", "head", "vp", "director"}
    recent_titles = [j.get("title", "").lower() for j in career[:2]]
    seniority = min(1.0, sum(
        1 for t in recent_titles if any(w in t for w in senior_words)
    ) / 2.0)

    has_current = any(j.get("is_current", False) for j in career)

    final = (0.40 * production_score +
             0.30 * industry_score +
             0.20 * seniority +
             0.10 * (1.0 if has_current else 0.0))

    return min(1.0, final), prod_hits > 0


def score_location(c: Dict) -> float:
    """Soft preference for India-based, bonus for Pune/Noida."""
    country  = c.get("profile", {}).get("country", "").lower()
    location = c.get("profile", {}).get("location", "").lower()
    relocate = c.get("redrob_signals", {}).get("willing_to_relocate", False)

    if country == "india":
        if any(city in location for city in ["pune", "noida", "gurugram", "gurgaon"]):
            return 1.00
        if any(city in location for city in [
                "bangalore", "bengaluru", "mumbai", "delhi",
                "hyderabad", "chennai", "kolkata"]):
            return 0.90
        return 0.80
    return 0.60 if relocate else 0.30


def fast_structured_score(c: Dict) -> float:
    """Lightweight composite for Stage 1 pre-filtering (no semantic model)."""
    sk, _    = score_skills(c)
    exp      = score_experience(c)
    beh      = score_behavioral(c)
    car, _   = score_career(c)
    loc      = score_location(c)
    hp       = honeypot_penalty(c)

    raw = (0.35 * sk + 0.20 * exp + 0.20 * beh + 0.15 * car + 0.10 * loc)
    return raw * (1.0 - 0.65 * hp)


# =========================================================================
# CANDIDATE TEXT BUILDER (for semantic encoding)
# =========================================================================

def build_candidate_text(c: Dict) -> str:
    """
    Compact text representation fed to the sentence encoder.
    Keeps under ~300 tokens to stay fast on CPU.
    """
    p      = c.get("profile", {})
    skills = c.get("skills", [])
    career = c.get("career_history", [])

    parts = [
        p.get("headline", ""),
        p.get("summary", "")[:280],
    ]
    top_skills = [s.get("name", "") for s in skills[:8]]
    if top_skills:
        parts.append("Skills: " + ", ".join(top_skills))

    for job in career[:2]:
        title = job.get("title", "")
        co    = job.get("company", "")
        desc  = job.get("description", "")[:140]
        parts.append(f"{title} at {co}: {desc}")

    return " ".join(p for p in parts if p).strip()


# =========================================================================
# REASONING GENERATOR
# =========================================================================

def make_reasoning(c: Dict, matched: List[str], has_prod: bool) -> str:
    """Specific, honest 1-2 sentence reasoning — no hallucination."""
    p  = c.get("profile", {})
    s  = c.get("redrob_signals", {})

    title   = p.get("current_title", "Engineer")
    yoe     = p.get("years_of_experience", 0)
    loc     = p.get("location", "")
    country = p.get("country", "")

    parts = [f"{title}, {yoe:.1f} yrs"]

    if country == "India":
        parts.append(loc)
    elif s.get("willing_to_relocate"):
        parts.append(f"{loc} (open to relocate)")

    if matched:
        parts.append("skills: " + ", ".join(matched[:3]))

    if has_prod:
        parts.append("production deployment evidence in career history")

    if s.get("open_to_work_flag"):
        parts.append("actively looking")

    rr = s.get("recruiter_response_rate", 0.5)
    if rr >= 0.75:
        parts.append(f"responsive ({rr:.0%} reply rate)")
    elif rr < 0.25:
        parts.append(f"low response rate ({rr:.0%}) — engagement risk")

    gh = s.get("github_activity_score", -1)
    if gh >= 65:
        parts.append(f"GitHub activity {gh:.0f}/100")
    elif gh == -1:
        parts.append("no GitHub linked")

    notice = s.get("notice_period_days", 0)
    if notice > 90:
        parts.append(f"notice period {notice}d")

    hp = honeypot_penalty(c)
    if hp >= 0.5:
        parts.append("NOTE: profile contains suspicious signal inconsistencies")

    return "; ".join(parts) + "."


# =========================================================================
# MAIN PIPELINE
# =========================================================================

def load_candidates(path: str) -> List[Dict]:
    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                candidates.append(json.loads(line))
    return candidates


def rank_candidates(candidates_path: str, output_path: str):
    t0 = time.time()
    print(f"[rank.py] Loading {candidates_path} ...")
    candidates = load_candidates(candidates_path)
    print(f"  Loaded {len(candidates):,} candidates in {time.time()-t0:.1f}s")

    # ------------------------------------------------------------------
    # Stage 1 — fast structured pre-filter  (all N → top 5 000)
    # ------------------------------------------------------------------
    print("[Stage 1] Structured pre-filter ...")
    t1 = time.time()

    scored1 = [(fast_structured_score(c), c) for c in candidates]
    scored1.sort(key=lambda x: x[0], reverse=True)
    top5k = scored1[:5000]
    print(f"  Done in {time.time()-t1:.1f}s | threshold={top5k[-1][0]:.4f}")

    # ------------------------------------------------------------------
    # Stage 2 — semantic scoring  (top 5 000 → cosine sim with JD)
    # ------------------------------------------------------------------
    print("[Stage 2] Semantic scoring with sentence-transformers ...")
    t2 = time.time()
    use_semantic = False
    semantic_scores = np.zeros(len(top5k))

    # CPU-only as required by submission spec
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    # Model priority: fast bi-encoders first, then fallback to structured-only
    MODEL_CANDIDATES = [
        "sentence-transformers/all-MiniLM-L6-v2",
        "all-MiniLM-L6-v2",
        "distilbert-base-uncased",   # already cached on server
    ]

    def _mean_pool(model_output, attention_mask):
        """Mean pooling for HF models used as sentence encoders."""
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(
            token_embeddings.size()).float()
        return (token_embeddings * input_mask_expanded).sum(1) / \
               input_mask_expanded.sum(1).clamp(min=1e-9)

    def encode_with_hf(model_name, texts, batch_size=128):
        import torch
        from transformers import AutoTokenizer, AutoModel
        import torch.nn.functional as F

        print(f"  Loading {model_name} ...")
        tok = AutoTokenizer.from_pretrained(model_name)
        mdl = AutoModel.from_pretrained(model_name)
        mdl.eval()

        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            encoded = tok(batch, padding=True, truncation=True,
                          max_length=256, return_tensors="pt")
            with torch.no_grad():
                out = mdl(**encoded)
            emb = _mean_pool(out, encoded["attention_mask"])
            emb = F.normalize(emb, p=2, dim=1)
            all_embs.append(emb.cpu().numpy())

        return np.vstack(all_embs)

    for model_name in MODEL_CANDIDATES:
        try:
            texts = [build_candidate_text(c) for _, c in top5k]
            all_texts = [JD_TEXT] + texts
            all_embs = encode_with_hf(model_name, all_texts)
            jd_emb, cand_emb = all_embs[0], all_embs[1:]
            semantic_scores = cand_emb @ jd_emb
            use_semantic = True
            print(f"  Done in {time.time()-t2:.1f}s using {model_name} | "
                  f"range [{semantic_scores.min():.3f}, {semantic_scores.max():.3f}]")
            break
        except Exception as exc:
            print(f"  {model_name} failed: {exc}")
    else:
        print("  All semantic models unavailable. Falling back to structured only.")

    # ------------------------------------------------------------------
    # Stage 3 — multi-signal combination + final ranking
    # ------------------------------------------------------------------
    print("[Stage 3] Multi-signal combination ...")

    results = []
    for i, (s1_score, c) in enumerate(top5k):
        sem  = float(semantic_scores[i])
        sk, matched = score_skills(c)
        exp  = score_experience(c)
        beh  = score_behavioral(c)
        car, has_prod = score_career(c)
        loc  = score_location(c)
        hp   = honeypot_penalty(c)

        if use_semantic:
            raw = (0.35 * sem  +
                   0.28 * sk   +
                   0.14 * car  +
                   0.12 * beh  +
                   0.06 * exp  +
                   0.05 * loc)
        else:
            raw = s1_score

        final = raw * (1.0 - 0.65 * hp)

        results.append({
            "candidate_id": c["candidate_id"],
            "score":        final,
            "matched":      matched,
            "has_prod":     has_prod,
            "candidate":    c,
        })

    # Sort: rounded score descending, tie-break candidate_id ascending (per spec)
    # Must use rounded score for tie-breaking since CSV scores are rounded to 4dp
    results.sort(key=lambda x: (-round(x["score"], 4), x["candidate_id"]))
    top100 = results[:100]

    # ------------------------------------------------------------------
    # Write output CSV
    # ------------------------------------------------------------------
    print(f"[Output] Writing {output_path} ...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, item in enumerate(top100, 1):
            writer.writerow([
                item["candidate_id"],
                rank,
                round(item["score"], 4),
                make_reasoning(item["candidate"], item["matched"], item["has_prod"]),
            ])

    elapsed = time.time() - t0
    print(f"\n[Done] {len(top100)} candidates ranked in {elapsed:.1f}s total")
    print("\nTop 10:")
    for rank, item in enumerate(top100[:10], 1):
        p = item["candidate"]["profile"]
        print(f"  {rank:2d}. {item['candidate_id']} | "
              f"{p.get('current_title','?')[:35]:<35} | "
              f"{p.get('years_of_experience',0):.1f}yr | "
              f"score={item['score']:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Rank candidates for Redrob JD")
    parser.add_argument("--candidates", default="./candidates.jsonl",
                        help="Path to candidates.jsonl")
    parser.add_argument("--out", default="./submission.csv",
                        help="Output CSV path")
    args = parser.parse_args()
    rank_candidates(args.candidates, args.out)


if __name__ == "__main__":
    main()
