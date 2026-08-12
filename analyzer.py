"""
Core financial metrics engine for the Startup Financial Health Analyzer.

Expects a monthly financial dataframe with (at minimum):
    month, revenue, cogs, opex, cash_balance

Optional columns (enable extra metrics if present):
    customers, new_customers, churned_customers, cac_spend

All functions are pure — they take a dataframe in and return a dataframe
or dict out, so they're easy to unit test independently of Streamlit.
"""

import pandas as pd
import numpy as np

REQUIRED_COLUMNS = ["month", "revenue", "cogs", "opex", "cash_balance"]
OPTIONAL_COLUMNS = ["customers", "new_customers", "churned_customers", "cac_spend"]


class DataValidationError(Exception):
    pass


def validate_columns(df: pd.DataFrame) -> list:
    """Return list of missing required columns (empty list = valid)."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return missing


def load_and_prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Clean types, sort by month, and return a prepared copy."""
    missing = validate_columns(df)
    if missing:
        raise DataValidationError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Required columns are: {', '.join(REQUIRED_COLUMNS)}."
        )

    df = df.copy()

    # Try to parse month as a real date for correct sorting; fall back to
    # treating it as an ordered categorical/string if parsing fails.
    parsed = pd.to_datetime(df["month"], errors="coerce")
    if parsed.notna().all():
        df["month"] = parsed
        df = df.sort_values("month").reset_index(drop=True)
        df["month_label"] = df["month"].dt.strftime("%b %Y")
    else:
        df["month_label"] = df["month"].astype(str)

    numeric_cols = ["revenue", "cogs", "opex", "cash_balance"] + [
        c for c in OPTIONAL_COLUMNS if c in df.columns and c != "customers"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[["revenue", "cogs", "opex", "cash_balance"]].isna().any().any():
        raise DataValidationError(
            "Some required numeric columns contain non-numeric or missing "
            "values. Please check your file for blanks or text in "
            "revenue / cogs / opex / cash_balance."
        )

    return df


def compute_core_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns: gross profit/margin, net burn, growth, etc."""
    df = df.copy()

    df["gross_profit"] = df["revenue"] - df["cogs"]
    df["gross_margin"] = np.where(
        df["revenue"] != 0, df["gross_profit"] / df["revenue"], np.nan
    )

    df["net_income"] = df["gross_profit"] - df["opex"]
    # Net burn: positive number = losing money that month
    df["net_burn"] = -df["net_income"]

    df["revenue_growth_mom"] = df["revenue"].pct_change()

    # Burn multiple = net burn / net new revenue generated that month.
    # High burn multiple = spending a lot to generate little new revenue.
    net_new_revenue = df["revenue"].diff()
    df["burn_multiple"] = np.where(
        net_new_revenue > 0, df["net_burn"] / net_new_revenue, np.nan
    )

    if "new_customers" in df.columns and "cac_spend" in df.columns:
        df["cac"] = np.where(
            df["new_customers"] > 0, df["cac_spend"] / df["new_customers"], np.nan
        )

    if "customers" in df.columns and "churned_customers" in df.columns:
        df["churn_rate"] = np.where(
            df["customers"] > 0, df["churned_customers"] / df["customers"], np.nan
        )

    return df


def compute_runway(df: pd.DataFrame, lookback_months: int = 3) -> dict:
    """
    Runway = current cash balance / average net burn over the last
    `lookback_months`. If the company is net profitable (avg burn <= 0),
    runway is treated as infinite.
    """
    current_cash = float(df["cash_balance"].iloc[-1])
    recent = df.tail(lookback_months)
    avg_burn = float(recent["net_burn"].mean())

    if avg_burn <= 0:
        return {
            "current_cash": current_cash,
            "avg_monthly_burn": avg_burn,
            "runway_months": float("inf"),
            "profitable": True,
        }

    return {
        "current_cash": current_cash,
        "avg_monthly_burn": avg_burn,
        "runway_months": current_cash / avg_burn,
        "profitable": False,
    }


def compute_summary(df: pd.DataFrame) -> dict:
    """One-stop summary dict used to drive the KPI cards and scoring."""
    runway_info = compute_runway(df)
    recent_growth = df["revenue_growth_mom"].tail(3).mean()
    recent_margin = df["gross_margin"].tail(3).mean()
    recent_burn_multiple = df["burn_multiple"].tail(3).mean()

    return {
        "current_cash": runway_info["current_cash"],
        "avg_monthly_burn": runway_info["avg_monthly_burn"],
        "runway_months": runway_info["runway_months"],
        "profitable": runway_info["profitable"],
        "latest_revenue": float(df["revenue"].iloc[-1]),
        "avg_mom_growth": recent_growth,
        "avg_gross_margin": recent_margin,
        "avg_burn_multiple": recent_burn_multiple,
    }
