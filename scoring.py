"""
Turns raw metrics into a single 0-100 Health Score with a letter grade
and a breakdown so users can see exactly why they got the score they did.

Weights and thresholds are intentionally simple and documented so they're
easy to defend, tune, or cite in a portfolio write-up.
"""

import math

WEIGHTS = {
    "runway": 0.35,
    "growth": 0.25,
    "margin": 0.20,
    "burn_efficiency": 0.20,
}


def _score_runway(runway_months: float) -> float:
    """0 pts at 0 months, 100 pts at 18+ months. Profitable = 100."""
    if runway_months == float("inf"):
        return 100.0
    return max(0.0, min(100.0, (runway_months / 18.0) * 100.0))


def _score_growth(avg_mom_growth: float) -> float:
    """
    0 pts at -10% MoM or worse, 100 pts at +15% MoM or better.
    Linear in between. NaN (e.g. only 1 month of data) -> neutral 50.
    """
    if avg_mom_growth is None or (isinstance(avg_mom_growth, float) and math.isnan(avg_mom_growth)):
        return 50.0
    lo, hi = -0.10, 0.15
    pct = (avg_mom_growth - lo) / (hi - lo)
    return max(0.0, min(100.0, pct * 100.0))


def _score_margin(avg_gross_margin: float) -> float:
    """0 pts at 0% margin, 100 pts at 80%+ margin. NaN -> neutral 50."""
    if avg_gross_margin is None or (isinstance(avg_gross_margin, float) and math.isnan(avg_gross_margin)):
        return 50.0
    return max(0.0, min(100.0, (avg_gross_margin / 0.80) * 100.0))


def _score_burn_efficiency(avg_burn_multiple: float) -> float:
    """
    Burn multiple: net burn / net new revenue. Lower is better.
    <=1x -> 100 pts, >=5x -> 0 pts. Negative (shrinking burn while growing)
    is capped at 100. NaN (e.g. no growth to divide by) -> neutral 50.
    """
    if avg_burn_multiple is None or (isinstance(avg_burn_multiple, float) and math.isnan(avg_burn_multiple)):
        return 50.0
    if avg_burn_multiple <= 1:
        return 100.0
    if avg_burn_multiple >= 5:
        return 0.0
    return 100.0 - ((avg_burn_multiple - 1) / 4.0) * 100.0


def compute_health_score(summary: dict) -> dict:
    """Returns overall score, letter grade, and per-category breakdown."""
    runway_score = _score_runway(summary["runway_months"])
    growth_score = _score_growth(summary["avg_mom_growth"])
    margin_score = _score_margin(summary["avg_gross_margin"])
    burn_score = _score_burn_efficiency(summary["avg_burn_multiple"])

    overall = (
        runway_score * WEIGHTS["runway"]
        + growth_score * WEIGHTS["growth"]
        + margin_score * WEIGHTS["margin"]
        + burn_score * WEIGHTS["burn_efficiency"]
    )

    if overall >= 85:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "overall": round(overall, 1),
        "grade": grade,
        "breakdown": {
            "Runway": round(runway_score, 1),
            "Growth": round(growth_score, 1),
            "Gross Margin": round(margin_score, 1),
            "Burn Efficiency": round(burn_score, 1),
        },
    }


def generate_insights(summary: dict, score: dict) -> list:
    """Plain-language, rule-based takeaways — no LLM call needed."""
    insights = []

    runway = summary["runway_months"]
    if summary["profitable"]:
        insights.append("The business is net profitable on a recent-months basis — runway is not a near-term constraint.")
    elif runway < 6:
        insights.append(f"Runway is critically short (~{runway:.1f} months). Fundraising or cutting burn should be the top priority.")
    elif runway < 12:
        insights.append(f"Runway is ~{runway:.1f} months. Most investors expect 12-18 months of runway — start planning the next raise now.")
    else:
        insights.append(f"Runway looks healthy at ~{runway:.1f} months.")

    growth = summary["avg_mom_growth"]
    if growth is not None and not (isinstance(growth, float) and growth != growth):
        if growth >= 0.15:
            insights.append(f"Strong momentum: revenue is growing ~{growth*100:.1f}% month-over-month on average.")
        elif growth >= 0.05:
            insights.append(f"Steady growth of ~{growth*100:.1f}% MoM, but there's room to accelerate.")
        elif growth >= 0:
            insights.append(f"Revenue growth is nearly flat (~{growth*100:.1f}% MoM) — worth investigating what's capping growth.")
        else:
            insights.append(f"Revenue is shrinking (~{growth*100:.1f}% MoM) — this needs immediate attention.")

    margin = summary["avg_gross_margin"]
    if margin is not None and not (isinstance(margin, float) and margin != margin):
        if margin >= 0.6:
            insights.append(f"Gross margin is strong at ~{margin*100:.1f}%, typical of a healthy software/product business.")
        elif margin >= 0.3:
            insights.append(f"Gross margin is moderate (~{margin*100:.1f}%) — check if COGS can be trimmed as you scale.")
        else:
            insights.append(f"Gross margin is thin (~{margin*100:.1f}%) — this will make growth expensive to fund.")

    bm = summary["avg_burn_multiple"]
    if bm is not None and not (isinstance(bm, float) and bm != bm):
        if bm <= 1:
            insights.append(f"Burn multiple of {bm:.1f}x is excellent — you're spending less than $1 to generate $1 of new revenue.")
        elif bm <= 2:
            insights.append(f"Burn multiple of {bm:.1f}x is reasonable for an early-stage company.")
        else:
            insights.append(f"Burn multiple of {bm:.1f}x is high — spending is outpacing the new revenue it's generating.")

    return insights
