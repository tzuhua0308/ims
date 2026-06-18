from __future__ import annotations
import pandas as pd
from typing import Optional
from utils.db import fetch_all, TABLES


def get_kpi(year: int, period: int) -> dict:
    purchases = fetch_all(TABLES["purchases"], {"year": year, "period": period})
    sales     = fetch_all(TABLES["sales"],     {"year": year, "period": period})
    expenses  = fetch_all(TABLES["expenses"],  {"year": year, "period": period})
    scraps    = fetch_all(TABLES["scraps"],    {"year": year, "period": period})
    products  = fetch_all(TABLES["products"])

    total_purchases = sum(r["amount"] or 0 for r in purchases)
    total_sales     = sum(r["untaxed_amount"] or 0 for r in sales)
    total_expenses  = sum(r["amount"] or 0 for r in expenses)
    total_scraps    = sum(r["loss"] or 0 for r in scraps)
    ref_price_total = sum(r["ref_price"] or 0 for r in products)

    # 期初庫存：第一期用品項主表合計；後續期別需遞推
    opening = _get_opening_inventory(year, period, ref_price_total)
    remaining = opening + total_purchases - total_sales - total_expenses - total_scraps

    return {
        "purchases": total_purchases,
        "sales": total_sales,
        "expenses": total_expenses,
        "scraps": total_scraps,
        "opening": opening,
        "remaining": remaining,
    }


def _get_opening_inventory(year: int, period: int, ref_price_total: float) -> float:
    if period == 1:
        return ref_price_total
    # 取上一期的剩餘庫存
    prev_period = period - 1
    prev_year   = year
    if prev_period == 0:
        prev_period = 6
        prev_year   = year - 1
    prev = get_kpi(prev_year, prev_period)
    return prev["remaining"]


def get_product_summary(year: int, period: int) -> pd.DataFrame:
    purchases = fetch_all(TABLES["purchases"], {"year": year, "period": period})
    sales     = fetch_all(TABLES["sales"],     {"year": year, "period": period})
    products  = fetch_all(TABLES["products"])

    df_p = pd.DataFrame(purchases)
    df_s = pd.DataFrame(sales)
    df_prod = pd.DataFrame(products) if products else pd.DataFrame(columns=["code","name","ref_price"])

    buy_by_code = (
        df_p.groupby("code")["amount"].sum().reset_index().rename(columns={"amount": "purchase_amt"})
        if not df_p.empty and "code" in df_p.columns else pd.DataFrame(columns=["code","purchase_amt"])
    )
    sell_by_code = (
        df_s.groupby("code")["untaxed_amount"].sum().reset_index().rename(columns={"untaxed_amount": "sales_amt"})
        if not df_s.empty and "code" in df_s.columns else pd.DataFrame(columns=["code","sales_amt"])
    )

    df = df_prod.merge(buy_by_code, on="code", how="outer").merge(sell_by_code, on="code", how="outer")
    df["purchase_amt"] = df["purchase_amt"].fillna(0)
    df["sales_amt"]    = df["sales_amt"].fillna(0)
    df["ref_price"]    = df["ref_price"].fillna(0)
    df["inventory"]    = df["ref_price"] + df["purchase_amt"] - df["sales_amt"]
    df["anomaly"]      = (df["sales_amt"] > 0) & (df["purchase_amt"] == 0)

    return df.sort_values("code").reset_index(drop=True)


def get_yearly_comparison(year1: int, year2: int) -> pd.DataFrame:
    rows = []
    for period in range(1, 7):
        for yr in [year1, year2]:
            sales     = fetch_all(TABLES["sales"],     {"year": yr, "period": period})
            purchases = fetch_all(TABLES["purchases"], {"year": yr, "period": period})
            rows.append({
                "year": yr,
                "period": period,
                "sales":     sum(r["untaxed_amount"] or 0 for r in sales),
                "purchases": sum(r["amount"] or 0 for r in purchases),
            })
    return pd.DataFrame(rows)


def period_label(period: int) -> str:
    months = {1:"1-2月",2:"3-4月",3:"5-6月",4:"7-8月",5:"9-10月",6:"11-12月"}
    return months.get(period, f"第{period}期")
