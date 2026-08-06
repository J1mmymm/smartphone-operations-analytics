"""Build the portfolio dataset from reconciled practicum control totals.

The public dataset is deterministic (seed 20260806), contains no personal
information, and does not depend on the private source workbook at runtime.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable


SEED = 20260806
START_DATE = date(2022, 1, 1)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
QA_DIR = ROOT / "data" / "quality"

QUARTER_SALES = {
    1: 0, 2: 0, 3: 0, 4: 0, 5: 1_802_500, 6: 1_297_400,
    7: 0, 8: 2_450_000, 9: 1_995_300, 10: 4_500_000,
    11: 4_287_500, 12: 3_675_000, 13: 5_512_500, 14: 7_350_000,
}

QUARTER_FAMILY_SALES = {
    5: {"L": 1_802_500},
    6: {"L": 1_297_400},
    8: {"L": 2_450_000},
    9: {"L": 573_300, "H": 1_422_000},
    10: {"H": 4_500_000},
    11: {"L": 4_287_500},
    12: {"L": 3_675_000},
    13: {"L": 5_512_500},
    14: {"L": 7_350_000},
}

QUARTER_CASH = {
    1: (0, 10_000_000, 8_256_000, 1_744_000),
    2: (1_744_000, 5_024_416, 6_251_900, 516_516),
    3: (516_516, 8_264, 410_000, 114_780),
    4: (114_780, 0, 0, 114_780),
    5: (114_780, 1_806_172, 1_776_207, 144_745),
    6: (144_745, 3_299_715, 3_118_000, 326_460),
    7: (326_460, 205_223, 469_000, 62_683),
    8: (62_683, 2_451_002, 2_350_650, 163_035),
    9: (163_035, 1_997_908, 2_114_000, 46_943),
    10: (46_943, 4_500_751, 4_224_500, 323_194),
    11: (323_194, 4_292_671, 4_515_500, 100_365),
    12: (100_365, 3_676_605, 3_439_250, 337_720),
    13: (337_720, 5_517_903, 5_852_400, 3_223),
    14: (3_223, 7_350_051, 7_000_000, 353_274),
}

# Exact quarter/category controls reconstructed from the 14 practicum rounds.
QUARTER_CATEGORIES = {
    1: {"financing_in": 10_000_000, "productive_fixed_assets": -4_500_000,
        "raw_material_warehouse": -800_000, "labor_cost": -216_000,
        "market_and_initial_product": -1_380_000, "raw_material_purchase": -360_000,
        "r_and_d": -1_000_000},
    2: {"interest_income": 24_416, "financing_in": 5_000_000,
        "productive_fixed_assets": -3_903_000, "raw_material_warehouse": -18_900,
        "labor_cost": -170_000, "market_and_initial_product": -600_000,
        "raw_material_purchase": -1_560_000},
    3: {"interest_income": 8_264, "labor_cost": -100_000,
        "staff_adjustment": -200_000, "loan_interest_penalty": -110_000},
    4: {},
    5: {"interest_income": 3_672, "sales_receipts": 1_802_500,
        "productive_fixed_assets": -44_307, "raw_material_warehouse": -12_900,
        "logistics": -99_000, "raw_material_purchase": -1_620_000},
    6: {"interest_income": 2_315, "sales_receipts": 1_297_400,
        "financing_in": 2_000_000, "labor_cost": -408_000,
        "raw_material_warehouse": -8_000, "productive_fixed_assets": -2_000,
        "raw_material_purchase": -2_400_000, "r_and_d": -300_000},
    7: {"interest_income": 5_223, "financing_in": 200_000,
        "productive_fixed_assets": -460_000, "logistics": -9_000},
    8: {"interest_income": 1_002, "sales_receipts": 2_450_000,
        "loan_interest_penalty": -4_000, "loan_principal_repayment": -200_000,
        "raw_material_purchase": -2_138_400, "logistics": -8_250},
    9: {"interest_income": 2_608, "sales_receipts": 1_995_300,
        "raw_material_purchase": -1_800_000, "logistics": -14_000,
        "r_and_d": -300_000},
    10: {"interest_income": 751, "sales_receipts": 4_500_000,
         "productive_fixed_assets": -2_400_000, "raw_material_purchase": -1_800_000,
         "logistics": -24_500},
    11: {"interest_income": 5_171, "sales_receipts": 4_287_500,
         "labor_cost": -26_000, "logistics": -13_500,
         "loan_principal_repayment": -2_000_000, "raw_material_purchase": -2_400_000,
         "loan_interest_penalty": -76_000},
    12: {"interest_income": 1_605, "sales_receipts": 3_675_000,
         "productive_fixed_assets": -600_000, "labor_cost": -80_000,
         "raw_material_purchase": -2_400_000, "loan_interest_penalty": -330_000,
         "logistics": -29_250},
    13: {"interest_income": 5_403, "sales_receipts": 5_512_500,
         "productive_fixed_assets": -405_400, "raw_material_warehouse": -4_000,
         "raw_material_purchase": -2_880_000, "logistics": -39_000,
         "loan_interest_penalty": -1_236_000, "labor_cost": -1_288_000},
    14: {"interest_income": 51, "sales_receipts": 7_350_000,
         "loan_principal_repayment": -5_000_000,
         "loan_interest_penalty": -200_000, "raw_material_purchase": -1_800_000},
}

PRODUCTS = [
    {"product_key": 101, "sku": "L1", "product_name": "N-Lite", "product_family": "L",
     "positioning": "大众基础款", "list_price": 2_699, "standard_unit_cost": 1_820,
     "launch_month_key": 202204},
    {"product_key": 102, "sku": "L2", "product_name": "N-Plus", "product_family": "L",
     "positioning": "大众升级款", "list_price": 3_299, "standard_unit_cost": 2_230,
     "launch_month_key": 202204},
    {"product_key": 201, "sku": "H1", "product_name": "N-Pro", "product_family": "H",
     "positioning": "高端旗舰款", "list_price": 4_599, "standard_unit_cost": 3_150,
     "launch_month_key": 202312},
    {"product_key": 202, "sku": "H2", "product_name": "N-Ultra", "product_family": "H",
     "positioning": "高端影像款", "list_price": 5_499, "standard_unit_cost": 3_820,
     "launch_month_key": 202312},
]

CHANNELS = [
    {"channel_key": 1, "channel_name": "线上直营", "channel_type": "Direct", "price_factor": 1.00},
    {"channel_key": 2, "channel_name": "线下零售", "channel_type": "Retail", "price_factor": 0.97},
    {"channel_key": 3, "channel_name": "区域经销", "channel_type": "Distributor", "price_factor": 0.91},
]

REGIONS = [
    {"region_key": 1, "region_name": "华东", "region_tier": "核心市场"},
    {"region_key": 2, "region_name": "华南", "region_tier": "核心市场"},
    {"region_key": 3, "region_name": "华北", "region_tier": "成长市场"},
    {"region_key": 4, "region_name": "中西部", "region_tier": "成长市场"},
]

CATEGORY_CN = {
    "sales_receipts": "销售回款", "financing_in": "融资及注资",
    "interest_income": "存款利息", "raw_material_purchase": "原材料采购",
    "productive_fixed_assets": "生产性固定资产", "raw_material_warehouse": "原材料仓储",
    "labor_cost": "人员成本", "r_and_d": "研发投入", "logistics": "物流运输",
    "loan_interest_penalty": "贷款利息及罚金", "loan_principal_repayment": "偿还贷款本金",
    "staff_adjustment": "人员调整", "market_and_initial_product": "市场推广与首批产品",
}


def add_months(d: date, months: int) -> date:
    month_index = d.year * 12 + d.month - 1 + months
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_key(d: date) -> int:
    return d.year * 100 + d.month


def allocate_integer(total: int, weights: Iterable[float]) -> list[int]:
    weights = list(weights)
    if total == 0:
        return [0] * len(weights)
    sign = 1 if total > 0 else -1
    total_abs = abs(int(total))
    weight_sum = sum(weights)
    raw = [total_abs * w / weight_sum for w in weights]
    base = [math.floor(x) for x in raw]
    remainder = total_abs - sum(base)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)
    for i in order[:remainder]:
        base[i] += 1
    return [sign * x for x in base]


def weighted_choice(rng: random.Random, rows: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    return rng.choices(rows, weights=weights, k=1)[0]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_dates() -> list[dict[str, Any]]:
    rows = []
    for i in range(42):
        d = add_months(START_DATE, i)
        q = i // 3 + 1
        rows.append({
            "date_key": month_key(d), "month_start": d.isoformat(), "year": d.year,
            "month_number": d.month, "month_label": f"{d.year}-{d.month:02d}",
            "quarter_seq": q, "business_quarter": f"Q{q:02d}",
            "year_quarter": f"{d.year}-Q{((d.month - 1) // 3) + 1}",
            "month_in_quarter": i % 3 + 1,
        })
    return rows


def build_sales(rng: random.Random, dates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order_num = 1
    product_by_family = {
        "L": [p for p in PRODUCTS if p["product_family"] == "L"],
        "H": [p for p in PRODUCTS if p["product_family"] == "H"],
    }
    dates_by_q = defaultdict(list)
    for d in dates:
        dates_by_q[d["quarter_seq"]].append(d)

    for q, family_amounts in QUARTER_FAMILY_SALES.items():
        month_rows = dates_by_q[q]
        base_month_weights = [0.28 + rng.random() * 0.08, 0.31 + rng.random() * 0.08, 0.36 + rng.random() * 0.08]
        for family, q_amount in family_amounts.items():
            monthly_amounts = allocate_integer(q_amount, base_month_weights)
            for mrow, m_amount in zip(month_rows, monthly_amounts):
                products = product_by_family[family]
                sku_mix = [0.62, 0.38] if family == "L" else [0.68, 0.32]
                blended_asp = sum(p["list_price"] * w for p, w in zip(products, sku_mix)) * 0.94
                total_units = max(1, round(m_amount / blended_asp))
                n_orders = max(8, min(26, round(total_units / 42)))
                qty_parts = allocate_integer(total_units, [0.5 + rng.random() for _ in range(n_orders)])
                revenue_parts = allocate_integer(m_amount, [qv * (0.93 + rng.random() * 0.14) for qv in qty_parts])

                for qty, net_sales in zip(qty_parts, revenue_parts):
                    product = weighted_choice(rng, products, sku_mix)
                    channel = weighted_choice(rng, CHANNELS, [0.29, 0.25, 0.46])
                    region = weighted_choice(rng, REGIONS, [0.34, 0.27, 0.22, 0.17])
                    unit_price = net_sales / qty
                    gross_sales = round(net_sales / max(0.80, channel["price_factor"]), 2)
                    discount = round(gross_sales - net_sales, 2)
                    unit_cost = product["standard_unit_cost"] * (0.985 + rng.random() * 0.045)
                    cogs = round(unit_cost * qty, 2)
                    # Prevent an implausible negative margin on a small residual order.
                    if cogs > net_sales * 0.86:
                        cogs = round(net_sales * (0.67 + rng.random() * 0.08), 2)
                        unit_cost = cogs / qty
                    order_day = min(24, 3 + int(rng.random() * 22))
                    od = date(mrow["year"], mrow["month_number"], order_day)
                    promise_days = 6 + int(rng.random() * 7)
                    promised = od + timedelta(days=promise_days)
                    rows.append({
                        "order_id": f"SO{order_num:05d}", "order_date_key": mrow["date_key"],
                        "order_date": od.isoformat(), "promised_date": promised.isoformat(),
                        "shipped_date": promised.isoformat(), "product_key": product["product_key"],
                        "channel_key": channel["channel_key"], "region_key": region["region_key"],
                        "ordered_qty": qty, "shipped_qty": qty, "unit_price": round(unit_price, 2),
                        "gross_sales": gross_sales, "discount_amount": discount,
                        "net_sales": round(float(net_sales), 2), "unit_cost": round(unit_cost, 2),
                        "cogs": cogs, "gross_profit": round(net_sales - cogs, 2),
                        "delivery_days": promise_days, "on_time_flag": 1, "full_fill_flag": 1,
                        "order_status": "Completed", "payment_term_days": [0, 15, 30][channel["channel_key"] - 1],
                    })
                    order_num += 1
    return rows


def monthly_capacity(quarter_seq: int) -> int:
    return {
        1: 250, 2: 250, 3: 270, 4: 290, 5: 300, 6: 310, 7: 330,
        8: 390, 9: 500, 10: 540, 11: 700, 12: 760, 13: 700, 14: 980,
    }[quarter_seq]


def monthly_warehouse_capacity(quarter_seq: int) -> int:
    if quarter_seq <= 6:
        return 520
    if quarter_seq <= 9:
        return 780
    if quarter_seq <= 11:
        return 1_100
    if quarter_seq == 12:
        return 1_550
    return 1_850


def build_operations(
    rng: random.Random, dates: list[dict[str, Any]], sales: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    demand: dict[tuple[int, int], int] = defaultdict(int)
    for row in sales:
        demand[(row["order_date_key"], row["product_key"])] += row["ordered_qty"]

    begin_inv = {101: 0, 102: 0, 201: 0, 202: 0}
    prod_rows: list[dict[str, Any]] = []
    inv_rows: list[dict[str, Any]] = []
    shipped_control: dict[tuple[int, int], int] = {}

    for idx, drow in enumerate(dates, start=1):
        key = drow["date_key"]
        q = drow["quarter_seq"]
        cap_total = monthly_capacity(q)
        wh_total = monthly_warehouse_capacity(q)
        needs: dict[int, int] = {}
        targets: dict[int, int] = {}
        for product in PRODUCTS:
            pk = product["product_key"]
            active = key >= product["launch_month_key"]
            m_demand = demand[(key, pk)]
            target = 0
            if active:
                target = 45 if product["product_family"] == "H" else 65
                if q >= 11:
                    target += 20
                if q == 13 and product["product_family"] == "L":
                    target += 35
            targets[pk] = target
            needs[pk] = max(0, m_demand + target - begin_inv[pk])

        total_need = sum(needs.values())
        if total_need == 0:
            cap_alloc = {p["product_key"]: cap_total // 4 for p in PRODUCTS}
            cap_alloc[PRODUCTS[-1]["product_key"]] += cap_total - sum(cap_alloc.values())
        else:
            cap_values = allocate_integer(cap_total, [needs[p["product_key"]] + 1 for p in PRODUCTS])
            cap_alloc = {p["product_key"]: cap_values[i] for i, p in enumerate(PRODUCTS)}

        wh_values = allocate_integer(wh_total, [1.15, 0.95, 0.75, 0.55])
        for i, product in enumerate(PRODUCTS):
            pk = product["product_key"]
            planned = needs[pk]
            gross_production = min(planned, cap_alloc[pk])
            defect_rate = 0.011 + rng.random() * 0.012
            defect_qty = round(gross_production * defect_rate)
            good_units = max(0, gross_production - defect_qty)
            available = begin_inv[pk] + good_units
            m_demand = demand[(key, pk)]
            shipped = min(m_demand, available)
            stockout = max(0, m_demand - shipped)
            ending = available - shipped
            days_supply = round((ending / max(1, m_demand)) * 30, 1) if m_demand else (90.0 if ending else 0.0)
            status = "缺货" if stockout > 0 else ("偏高" if days_supply > 45 else ("偏低" if m_demand and days_supply < 8 else "健康"))
            downtime = round((1.5 + rng.random() * 8.5) * (1.15 if q == 13 else 1), 1)
            util = gross_production / cap_alloc[pk] if cap_alloc[pk] else 0
            overtime = round(max(0, util - 0.82) * 160 + rng.random() * 3, 1)
            prod_rows.append({
                "month_key": key, "product_key": pk, "planned_units": planned,
                "actual_good_units": good_units, "defect_units": defect_qty,
                "capacity_allocated_units": cap_alloc[pk], "downtime_hours": downtime,
                "overtime_hours": overtime, "capacity_utilization": round(util, 4),
            })
            inv_rows.append({
                "month_key": key, "product_key": pk, "beginning_inventory_qty": begin_inv[pk],
                "production_receipts_qty": good_units, "demand_qty": m_demand,
                "shipped_qty": shipped, "ending_inventory_qty": ending, "stockout_qty": stockout,
                "inventory_value": round(ending * product["standard_unit_cost"], 2),
                "warehouse_capacity_qty": wh_values[i], "days_of_supply": days_supply,
                "inventory_status": status,
            })
            shipped_control[(key, pk)] = shipped
            begin_inv[pk] = ending

    # Allocate operational shipment constraints back to order lines.
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in sales:
        grouped[(row["order_date_key"], row["product_key"])].append(row)
    for group_key, orders in grouped.items():
        remaining = shipped_control[group_key]
        q = next(d["quarter_seq"] for d in dates if d["date_key"] == group_key[0])
        for row in sorted(orders, key=lambda x: x["order_date"]):
            shipped = min(row["ordered_qty"], remaining)
            remaining -= shipped
            full = int(shipped == row["ordered_qty"])
            promised = date.fromisoformat(row["promised_date"])
            if full:
                delay = 0 if rng.random() > (0.07 + 0.06 * (q == 13)) else 1 + int(rng.random() * 5)
            else:
                delay = 8 + int(rng.random() * 17)
            shipped_date = promised + timedelta(days=delay)
            row["shipped_qty"] = shipped
            row["shipped_date"] = shipped_date.isoformat()
            row["delivery_days"] = (shipped_date - date.fromisoformat(row["order_date"])).days
            row["full_fill_flag"] = full
            row["on_time_flag"] = int(full and delay == 0)
            row["order_status"] = "Completed" if full else ("Partial" if shipped else "Backorder")
    return prod_rows, inv_rows


def build_cashflow(rng: random.Random, dates: list[dict[str, Any]], sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
    monthly_sales: dict[int, int] = defaultdict(int)
    for row in sales:
        monthly_sales[row["order_date_key"]] += int(round(row["net_sales"]))
    dates_by_q: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for d in dates:
        dates_by_q[d["quarter_seq"]].append(d)

    rows: list[dict[str, Any]] = []
    tx_num = 1
    for q in range(1, 15):
        qdates = dates_by_q[q]
        for category, signed_total in QUARTER_CATEGORIES[q].items():
            if category == "sales_receipts":
                splits = [monthly_sales[d["date_key"]] for d in qdates]
                assert sum(splits) == signed_total
            else:
                splits = allocate_integer(signed_total, [0.25 + rng.random() * 0.15, 0.31 + rng.random() * 0.15, 0.39 + rng.random() * 0.15])
            for drow, signed in zip(qdates, splits):
                if signed == 0:
                    continue
                direction = "Inflow" if signed > 0 else "Outflow"
                transaction_date = date(drow["year"], drow["month_number"], 18)
                rows.append({
                    "cashflow_id": f"CF{tx_num:04d}", "date_key": drow["date_key"],
                    "transaction_date": transaction_date.isoformat(), "quarter_seq": q,
                    "flow_direction": direction, "flow_category": category,
                    "flow_category_cn": CATEGORY_CN[category], "amount": abs(signed),
                    "signed_amount": signed, "control_source": "practicum_reconciled",
                })
                tx_num += 1
    return rows


def build_monthly_kpis(
    dates: list[dict[str, Any]], sales: list[dict[str, Any]], production: list[dict[str, Any]],
    inventory: list[dict[str, Any]], cashflow: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = []
    cumulative_cash = 0
    for d in dates:
        key = d["date_key"]
        s = [r for r in sales if r["order_date_key"] == key]
        p = [r for r in production if r["month_key"] == key]
        i = [r for r in inventory if r["month_key"] == key]
        c = [r for r in cashflow if r["date_key"] == key]
        revenue = sum(r["net_sales"] for r in s)
        cogs = sum(r["cogs"] for r in s)
        ordered = sum(r["ordered_qty"] for r in s)
        shipped = sum(r["shipped_qty"] for r in s)
        cumulative_cash += sum(r["signed_amount"] for r in c)
        prod_actual = sum(r["actual_good_units"] + r["defect_units"] for r in p)
        capacity = sum(r["capacity_allocated_units"] for r in p)
        inv_value = sum(r["inventory_value"] for r in i)
        out.append({
            "date_key": key, "month_label": d["month_label"], "quarter_seq": d["quarter_seq"],
            "business_quarter": d["business_quarter"], "net_sales": round(revenue, 2),
            "gross_profit": round(revenue - cogs, 2),
            "gross_margin": round((revenue - cogs) / revenue, 4) if revenue else 0,
            "ordered_qty": ordered, "shipped_qty": shipped,
            "fill_rate": round(shipped / ordered, 4) if ordered else 0,
            "on_time_order_rate": round(sum(r["on_time_flag"] for r in s) / len(s), 4) if s else 0,
            "ending_inventory_value": round(inv_value, 2),
            "capacity_utilization": round(prod_actual / capacity, 4) if capacity else 0,
            "net_cashflow": sum(r["signed_amount"] for r in c), "closing_cash": cumulative_cash,
        })
    return out


def build_quarterly_kpis(monthly: list[dict[str, Any]], sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for q in range(1, 15):
        months = [r for r in monthly if r["quarter_seq"] == q]
        s = [r for r in sales if ((r["order_date_key"] // 100 - START_DATE.year) * 12 + (r["order_date_key"] % 100 - 1)) // 3 + 1 == q]
        revenue = sum(r["net_sales"] for r in s)
        cogs = sum(r["cogs"] for r in s)
        ordered = sum(r["ordered_qty"] for r in s)
        shipped = sum(r["shipped_qty"] for r in s)
        opening, inflow, outflow, closing = QUARTER_CASH[q]
        prev_sales = QUARTER_SALES.get(q - 1, 0)
        rows.append({
            "quarter_seq": q, "business_quarter": f"Q{q:02d}", "net_sales": round(revenue, 2),
            "sales_qoq_growth": round((revenue - prev_sales) / prev_sales, 4) if prev_sales else 0,
            "gross_profit": round(revenue - cogs, 2),
            "gross_margin": round((revenue - cogs) / revenue, 4) if revenue else 0,
            "ordered_qty": ordered, "shipped_qty": shipped,
            "fill_rate": round(shipped / ordered, 4) if ordered else 0,
            "on_time_order_rate": round(sum(r["on_time_flag"] for r in s) / len(s), 4) if s else 0,
            "avg_inventory_value": round(sum(m["ending_inventory_value"] for m in months) / 3, 2),
            "inventory_turnover": round(cogs / max(1, sum(m["ending_inventory_value"] for m in months) / 3), 2) if revenue else 0,
            "capacity_utilization": round(sum(m["capacity_utilization"] for m in months) / 3, 4),
            "opening_cash": opening, "cash_inflow": inflow, "cash_outflow": outflow,
            "net_cashflow": inflow - outflow, "closing_cash": closing,
        })
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_and_summarize(
    dates: list[dict[str, Any]], sales: list[dict[str, Any]], production: list[dict[str, Any]],
    inventory: list[dict[str, Any]], cashflow: list[dict[str, Any]], quarterly: list[dict[str, Any]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, actual: Any, expected: Any) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "actual": actual, "expected": expected})

    check("date_rows", len(dates) == 42, len(dates), 42)
    check("date_key_unique", len({r["date_key"] for r in dates}) == len(dates), len({r["date_key"] for r in dates}), len(dates))
    check("order_id_unique", len({r["order_id"] for r in sales}) == len(sales), len({r["order_id"] for r in sales}), len(sales))
    check("positive_order_values", all(r["ordered_qty"] > 0 and r["net_sales"] > 0 and r["cogs"] >= 0 for r in sales), "all valid", "all valid")
    check("shipment_not_above_order", all(0 <= r["shipped_qty"] <= r["ordered_qty"] for r in sales), "all valid", "all valid")
    check("sales_total", round(sum(r["net_sales"] for r in sales)) == 32_870_200, round(sum(r["net_sales"] for r in sales)), 32_870_200)
    family_totals = defaultdict(float)
    pmap = {p["product_key"]: p for p in PRODUCTS}
    for r in sales:
        family_totals[pmap[r["product_key"]]["product_family"]] += r["net_sales"]
    check("L_family_total", round(family_totals["L"]) == 26_948_200, round(family_totals["L"]), 26_948_200)
    check("H_family_total", round(family_totals["H"]) == 5_922_000, round(family_totals["H"]), 5_922_000)
    check("cash_inflow_total", sum(r["amount"] for r in cashflow if r["flow_direction"] == "Inflow") == 50_130_681, sum(r["amount"] for r in cashflow if r["flow_direction"] == "Inflow"), 50_130_681)
    check("cash_outflow_total", sum(r["amount"] for r in cashflow if r["flow_direction"] == "Outflow") == 49_777_407, sum(r["amount"] for r in cashflow if r["flow_direction"] == "Outflow"), 49_777_407)
    check("ending_cash", sum(r["signed_amount"] for r in cashflow) == 353_274, sum(r["signed_amount"] for r in cashflow), 353_274)
    q_cash_ok = all(qr["opening_cash"] + qr["net_cashflow"] == qr["closing_cash"] for qr in quarterly)
    check("quarter_cash_reconciliation", q_cash_ok, "14/14", "14/14")
    check("production_inventory_balance", all(r["beginning_inventory_qty"] + r["production_receipts_qty"] - r["shipped_qty"] == r["ending_inventory_qty"] for r in inventory), "all valid", "all valid")

    total_sales = sum(r["net_sales"] for r in sales)
    total_cogs = sum(r["cogs"] for r in sales)
    ordered = sum(r["ordered_qty"] for r in sales)
    shipped = sum(r["shipped_qty"] for r in sales)
    channel_sales = defaultdict(float)
    region_sales = defaultdict(float)
    for r in sales:
        channel_sales[r["channel_key"]] += r["net_sales"]
        region_sales[r["region_key"]] += r["net_sales"]
    top_channel_key = max(channel_sales, key=channel_sales.get)
    top_region_key = max(region_sales, key=region_sales.get)
    q13 = next(r for r in quarterly if r["quarter_seq"] == 13)
    q14 = next(r for r in quarterly if r["quarter_seq"] == 14)
    findings = {
        "total_sales": round(total_sales, 2),
        "gross_margin": round((total_sales - total_cogs) / total_sales, 4),
        "fill_rate": round(shipped / ordered, 4),
        "on_time_order_rate": round(sum(r["on_time_flag"] for r in sales) / len(sales), 4),
        "top_channel": next(c["channel_name"] for c in CHANNELS if c["channel_key"] == top_channel_key),
        "top_channel_share": round(channel_sales[top_channel_key] / total_sales, 4),
        "top_region": next(r["region_name"] for r in REGIONS if r["region_key"] == top_region_key),
        "top_region_share": round(region_sales[top_region_key] / total_sales, 4),
        "L_family_share": round(family_totals["L"] / total_sales, 4),
        "q13_fill_rate": q13["fill_rate"], "q14_fill_rate": q14["fill_rate"],
        "q13_capacity_utilization": q13["capacity_utilization"],
        "q14_capacity_utilization": q14["capacity_utilization"],
        "minimum_quarter_closing_cash": min(r["closing_cash"] for r in quarterly),
        "minimum_cash_quarter": min(quarterly, key=lambda r: r["closing_cash"])["business_quarter"],
        "q14_sales_growth": q14["sales_qoq_growth"],
    }
    return {
        "seed": SEED, "source_description": "基于专业见习经营流水整理并补全的项目数据",
        "coverage": {"start_month": dates[0]["month_label"], "end_month": dates[-1]["month_label"], "months": 42, "quarters": 14},
        "row_counts": {"dim_date": len(dates), "dim_product": len(PRODUCTS), "dim_channel": len(CHANNELS), "dim_region": len(REGIONS), "fact_sales_order": len(sales), "fact_production": len(production), "fact_inventory": len(inventory), "fact_cashflow": len(cashflow)},
        "checks": checks, "overall_status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
        "findings": findings,
    }


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    dates = build_dates()
    sales = build_sales(rng, dates)
    production, inventory = build_operations(rng, dates, sales)
    cashflow = build_cashflow(rng, dates, sales)
    monthly = build_monthly_kpis(dates, sales, production, inventory, cashflow)
    quarterly = build_quarterly_kpis(monthly, sales)

    write_csv(DATA_DIR / "dim_date.csv", dates)
    write_csv(DATA_DIR / "dim_product.csv", PRODUCTS)
    write_csv(DATA_DIR / "dim_channel.csv", CHANNELS)
    write_csv(DATA_DIR / "dim_region.csv", REGIONS)
    write_csv(DATA_DIR / "fact_sales_order.csv", sales)
    write_csv(DATA_DIR / "fact_production.csv", production)
    write_csv(DATA_DIR / "fact_inventory.csv", inventory)
    write_csv(DATA_DIR / "fact_cashflow.csv", cashflow)
    write_csv(DATA_DIR / "mart_monthly_kpi.csv", monthly)
    write_csv(DATA_DIR / "mart_quarterly_kpi.csv", quarterly)

    qa = validate_and_summarize(dates, sales, production, inventory, cashflow, quarterly)
    files = sorted(DATA_DIR.glob("*.csv"))
    qa["file_hashes"] = {p.name: sha256(p) for p in files}
    (QA_DIR / "qa_report.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(QA_DIR / "qa_checks.csv", qa["checks"])
    (ROOT / "outputs" / "analysis_summary.json").write_text(json.dumps(qa["findings"], ensure_ascii=False, indent=2), encoding="utf-8")
    if qa["overall_status"] != "PASS":
        raise SystemExit("Data quality checks failed; inspect data/quality/qa_report.json")
    print(json.dumps({"status": qa["overall_status"], "rows": qa["row_counts"], "findings": qa["findings"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

