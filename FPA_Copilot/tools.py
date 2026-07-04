"""
Deterministic "worker" tools for the FP&A Copilot orchestrator.
Each tool is plain Python — no LLM involved in the logic itself. The LLM
orchestrator (orchestrator.py) only decides WHICH tool to call and WHAT
arguments to pass; the actual judgment (materiality gates, Confirmed-vs-
Hypothesis, duplicate detection) is deterministic and auditable, same
discipline as the Month-End Close Toolkit and the Forecasting Agent.
"""
from pathlib import Path

import duckdb

WAREHOUSE_PATH = Path(__file__).parent.parent / "fpa_data_layer" / "warehouse.duckdb"


def get_forecast(company: str) -> dict:
    """Pull the 8-quarter forecast + driver context for a company from the
    Data Layer warehouse (dbt mart fct_company_forecast)."""
    con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    rows = con.execute(
        """
        SELECT company, quarter, low_musd, base_case_musd, high_musd,
               base_quarter, revenue_growth_trailing_pct, ndr_overall_pct,
               ndr_direction, known_gaps_count
        FROM main.fct_company_forecast
        WHERE company ILIKE ?
        ORDER BY quarter_index
        """,
        [f"%{company}%"],
    ).fetchall()
    con.close()

    if not rows:
        return {"error": f"No data found for company matching '{company}'. "
                          f"Available companies must be loaded via fpa_data_layer/load_raw.py first."}

    distinct_companies = sorted(set(r[0] for r in rows))
    if len(distinct_companies) > 1:
        return {"error": f"'{company}' matched multiple companies: {distinct_companies}. "
                          f"Be more specific (e.g. use the ticker in parentheses)."}

    quarters = [
        {"quarter": r[1], "low_musd": r[2], "base_case_musd": r[3], "high_musd": r[4]}
        for r in rows
    ]
    first = rows[0]
    return {
        "company": first[0],
        "base_quarter": first[5],
        "trailing_growth_pct": first[6],
        "ndr_pct": first[7],
        "ndr_direction": first[8],
        "known_data_gaps": first[9],
        "forecast_quarters": quarters,
    }


def get_variance_commentary(line_items: list, materiality_threshold_usd: float = 10000) -> dict:
    """
    Deterministic P&L variance commentary — same judgment as the Month-End
    Close Toolkit's Example 1: materiality gate, Confirmed-vs-Hypothesis
    discipline, hard sign-off gate for unexplained material variances.

    line_items: list of dicts, each:
        {"name": str, "actual": float, "budget": float, "known_reason": str or None}
    If known_reason is provided, the variance is CONFIRMED. If not and the
    variance is material, it's flagged HYPOTHESIS / OPEN — never silently
    stated as fact.
    """
    results = []
    open_items = []
    total_unexplained_material = 0.0

    for item in line_items:
        variance = item["actual"] - item["budget"]
        pct = (variance / item["budget"] * 100) if item["budget"] else 0.0
        material = abs(variance) >= materiality_threshold_usd
        status = "CONFIRMED" if item.get("known_reason") else ("HYPOTHESIS" if material else "immaterial")

        entry = {
            "name": item["name"],
            "variance_usd": round(variance, 2),
            "variance_pct": round(pct, 2),
            "material": material,
            "status": status,
            "reason": item.get("known_reason"),
        }
        results.append(entry)

        if material and not item.get("known_reason"):
            open_items.append(entry)
            total_unexplained_material += abs(variance)

    sign_off_blocked = len(open_items) > 0

    return {
        "line_items": results,
        "sign_off_status": "BLOCKED — open items must clear first" if sign_off_blocked else "CLEAR",
        "open_items": open_items,
        "total_unexplained_material_usd": round(total_unexplained_material, 2),
    }


def get_reconciliation_check(net_diff_usd: float, explained_usd: float, items: list) -> dict:
    """
    Deterministic reconciliation exception review — same judgment as the
    Month-End Close Toolkit's Example 2: a rec that mathematically ties can
    still be BLOCKED if a reconciling item is a duplicate or otherwise high-risk.

    items: list of dicts, each:
        {"description": str, "amount": float, "category": str}
        category examples: "duplicate", "timing", "unclassified"
    """
    unexplained = round(net_diff_usd - explained_usd, 2)
    ties = abs(unexplained) < 0.01

    blockers = [
        item for item in items
        if item.get("category") in ("duplicate", "unclassified") and abs(item["amount"]) >= 1000
    ]

    sign_off_status = "CLEAR"
    if blockers:
        sign_off_status = "BLOCKED — high-risk reconciling item(s) present, math tying is not sufficient"
    elif not ties:
        sign_off_status = "BLOCKED — unexplained residual remains"

    return {
        "net_diff_usd": net_diff_usd,
        "explained_usd": explained_usd,
        "unexplained_usd": unexplained,
        "mathematically_ties": ties,
        "blockers": blockers,
        "sign_off_status": sign_off_status,
    }


# --- Tool schemas for LLM function/tool calling (OpenAI-compatible format) ---

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get the 8-quarter driver-based revenue forecast and SaaS driver context "
                            "(NDR, growth trend) for a company already loaded in the Data Layer warehouse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name or ticker, e.g. 'MNDY' or 'Asana'"}
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_variance_commentary",
            "description": "Generate P&L variance commentary for a set of line items, applying a "
                            "materiality gate and Confirmed-vs-Hypothesis discipline. Use when the user "
                            "gives actual vs. budget figures and wants variance analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "actual": {"type": "number"},
                                "budget": {"type": "number"},
                                "known_reason": {
                                    "type": "string",
                                    "description": "Optional. If provided, variance is marked CONFIRMED.",
                                },
                            },
                            "required": ["name", "actual", "budget"],
                        },
                    },
                    "materiality_threshold_usd": {"type": "number", "description": "Default 10000"},
                },
                "required": ["line_items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reconciliation_check",
            "description": "Review a reconciliation for sign-off, checking whether it should be "
                            "BLOCKED even if the math ties (e.g. a duplicate payment hiding in the "
                            "reconciling items). Use when the user describes a rec with a net "
                            "difference, explained amount, and reconciling items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "net_diff_usd": {"type": "number"},
                    "explained_usd": {"type": "number"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "amount": {"type": "number"},
                                "category": {
                                    "type": "string",
                                    "description": "e.g. 'duplicate', 'timing', 'unclassified'",
                                },
                            },
                            "required": ["description", "amount", "category"],
                        },
                    },
                },
                "required": ["net_diff_usd", "explained_usd", "items"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_forecast": get_forecast,
    "get_variance_commentary": get_variance_commentary,
    "get_reconciliation_check": get_reconciliation_check,
}


if __name__ == "__main__":
    # Quick self-test, no LLM involved
    print(get_forecast("MNDY"))
    print()
    print(get_variance_commentary([
        {"name": "Revenue", "actual": 1240000, "budget": 1180000, "known_reason": "new client wins"},
        {"name": "Direct Costs", "actual": 496000, "budget": 448400},
    ]))
    print()
    print(get_reconciliation_check(11800, 11800, [
        {"description": "Vendor #0871 invoice posted twice", "amount": 11500, "category": "duplicate"}
    ]))
