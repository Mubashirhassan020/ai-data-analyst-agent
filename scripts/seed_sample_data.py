"""Generates the two sample datasets shipped in data/sample/, used to explore
the app without needing your own data. Both are synthetic (numpy, fixed seed)
but deliberately messy: missing values, outliers, categorical and datetime
columns, and a couple of duplicate rows — so profiling/quality-scoring/
visualization/AI-analysis all have something real to find.

Run: python scripts/seed_sample_data.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).parent.parent / "data" / "sample"


def make_ecommerce_sales(n: int = 220, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    categories = ["Electronics", "Home & Kitchen", "Clothing", "Sports", "Books"]
    regions = ["North", "South", "East", "West"]
    payment_methods = ["Credit Card", "PayPal", "Debit Card", "Gift Card"]

    category = rng.choice(categories, n, p=[0.3, 0.2, 0.25, 0.15, 0.1])
    base_price = {"Electronics": 220, "Home & Kitchen": 60, "Clothing": 35, "Sports": 50, "Books": 15}
    unit_price = np.array([base_price[c] for c in category]) * rng.uniform(0.7, 1.4, n)
    unit_price = unit_price.round(2)

    quantity = rng.integers(1, 6, n)
    discount_pct = rng.choice([0, 5, 10, 15, 20], n, p=[0.5, 0.2, 0.15, 0.1, 0.05]).astype(float)

    revenue = (unit_price * quantity * (1 - discount_pct / 100)).round(2)
    # Inject a few genuine outliers (bulk/wholesale-looking orders).
    outlier_idx = rng.choice(n, size=4, replace=False)
    revenue[outlier_idx] = revenue[outlier_idx] * rng.uniform(8, 15, 4)

    order_date = pd.date_range("2025-01-01", periods=n, freq="7h") + pd.to_timedelta(
        rng.integers(0, 60, n), unit="D"
    )

    df = pd.DataFrame({
        "order_id": [f"ORD-{i:05d}" for i in range(1, n + 1)],
        "customer_name": [f"Customer {i}" for i in rng.integers(1, 150, n)],
        "category": category,
        "region": rng.choice(regions, n),
        "order_date": order_date,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "revenue": revenue,
        "payment_method": rng.choice(payment_methods, n),
    })

    # Missing values: a realistic slice of discount_pct and payment_method unset.
    df.loc[rng.choice(n, size=15, replace=False), "discount_pct"] = np.nan
    df.loc[rng.choice(n, size=8, replace=False), "payment_method"] = np.nan

    # A couple of genuine duplicate rows (e.g. a double-submitted order).
    df = pd.concat([df, df.iloc[[3, 40]]], ignore_index=True)

    return df.sort_values("order_date").reset_index(drop=True)


def make_financial_transactions(n: int = 200, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    tx_types = ["purchase", "refund", "transfer", "withdrawal", "deposit"]
    categories = ["Groceries", "Utilities", "Entertainment", "Travel", "Salary", "Rent", "Other"]
    merchants = ["Acme Store", "City Utilities", "StreamCo", "Airline Co", "Employer Inc", "Landlord LLC", None]

    tx_type = rng.choice(tx_types, n, p=[0.45, 0.05, 0.1, 0.15, 0.25])
    amount_sign = np.where(np.isin(tx_type, ["deposit", "refund"]), 1, -1)
    amount = (amount_sign * rng.gamma(3.0, 60.0, n)).round(2)

    # A handful of large, fraud-like outlier transactions.
    outlier_idx = rng.choice(n, size=5, replace=False)
    amount[outlier_idx] = -rng.uniform(3000, 9000, 5)

    balance = 5000 + np.cumsum(amount)

    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i:06d}" for i in range(1, n + 1)],
        "account_id": rng.choice([f"ACC-{i:03d}" for i in range(1, 21)], n),
        "transaction_date": pd.date_range("2025-01-01", periods=n, freq="9h"),
        "transaction_type": tx_type,
        "category": rng.choice(categories, n),
        "merchant": rng.choice(merchants, n, p=[0.2, 0.15, 0.15, 0.1, 0.15, 0.1, 0.15]),
        "amount": amount,
        "balance_after": balance.round(2),
    })

    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sales = make_ecommerce_sales()
    sales_path = OUT_DIR / "ecommerce_sales.csv"
    sales.to_csv(sales_path, index=False)
    print(f"Wrote {sales_path} ({len(sales)} rows)")

    finance = make_financial_transactions()
    finance_path = OUT_DIR / "financial_transactions.csv"
    finance.to_csv(finance_path, index=False)
    print(f"Wrote {finance_path} ({len(finance)} rows)")


if __name__ == "__main__":
    main()
