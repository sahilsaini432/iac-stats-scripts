#!/usr/bin/env python3
"""
summarize_category_lines_per_month.py

Iterate over JSONs in 'repo_data/', sum lines_changed per category, and
normalize by the repository's age in months (earliest -> latest commit).
Also prints the average per month as a percentage of the repo's total avg/month.

Assumptions about each JSON (your earlier collector's format):
{
  "<commit_sha>": {
    "sha": "...",
    "Author": "...",
    "Date": "YYYY-MM-DDTHH:MM:SSZ",
    "Files": [
      {"filename": "...", "lines_changed": <int>, "category": "Development" | "Test" | ...},
      ...
    ]
  },
  ...
}

Usage:
  python summarize_category_lines_per_month.py
  python summarize_category_lines_per_month.py --dir repo_data
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

MEAN_DAYS_PER_MONTH = 30.4375  # 365.25 / 12

def parse_args():
    ap = argparse.ArgumentParser(description="Sum lines_changed per category and average per month (with % share).")
    ap.add_argument("--dir", "-d", default="repo_data",
                    help="Directory containing *.json files (default: repo_data)")
    return ap.parse_args()

def parse_iso8601_z(dt_str: str) -> datetime:
    """
    Parse ISO8601 strings like '2025-08-11T15:17:37Z' (or with offset).
    Returns an aware datetime in UTC.
    """
    s = dt_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def normalize_category(cat: str) -> str:
    if not cat:
        return "Uncategorized"
    c = cat.strip()
    if c.lower() == "development":
        return "Development"
    return c.title()

def summarize_file(json_path: Path):
    # Read JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Collect commit dates + category totals
    dates = []
    category_totals = defaultdict(int)
    commit_count = 0

    for sha, obj in (data or {}).items():
        if not isinstance(obj, dict):
            continue
        date_str = obj.get("Date")
        if date_str:
            try:
                dates.append(parse_iso8601_z(date_str))
            except Exception:
                pass

        files = obj.get("Files") or []
        if isinstance(files, list):
            for fobj in files:
                if not isinstance(fobj, dict):
                    continue
                cat = normalize_category(fobj.get("category"))
                lc = fobj.get("lines_changed", 0)
                try:
                    lc_int = int(lc)
                except Exception:
                    # Try float->int if strings sneak in, else skip
                    try:
                        lc_int = int(float(lc))
                    except Exception:
                        lc_int = 0
                category_totals[cat] += lc_int
        commit_count += 1

    # Compute age
    if dates:
        earliest = min(dates)
        latest = max(dates)
        delta_days = (latest - earliest).days
        age_months = delta_days / MEAN_DAYS_PER_MONTH if delta_days > 0 else 0.0
    else:
        earliest = latest = None
        delta_days = 0
        age_months = 0.0

    return {
        "repo": json_path.stem,
        "earliest": earliest.date().isoformat() if earliest else "",
        "latest": latest.date().isoformat() if latest else "",
        "age_days": delta_days,
        "age_months": round(age_months, 2),
        "commit_count": commit_count,
        "category_totals": dict(sorted(category_totals.items())),
    }

def print_repo_summary(summary):
    repo = summary["repo"]
    earliest = summary["earliest"]
    latest = summary["latest"]
    age_days = summary["age_days"]
    age_months = summary["age_months"]
    commit_count = summary["commit_count"]
    totals = summary["category_totals"]

    # Header
    print(f"\n=== {repo} ===")
    print(f"Earliest commit: {earliest or 'N/A'}   Latest commit: {latest or 'N/A'}")
    print(f"Age: {age_days} days  (~{age_months} months)   Commits in JSON: {commit_count}")

    # Table
    cat_header = "Category"
    tot_header = "Total Lines Changed"
    permo_header = "Avg per Month"
    perc_header = "Avg/mo %"

    # Compute per-month averages
    per_month = {}
    for cat, total in totals.items():
        if age_months > 0:
            per_month[cat] = total / age_months
        else:
            per_month[cat] = None

    # Grand totals for percentage calculation
    grand_total = sum(totals.values())
    grand_avg = (grand_total / age_months) if age_months > 0 else None

    # Compute percentages (category avg per month / total avg per month)
    per_month_pct = {}
    for cat, avg in per_month.items():
        if avg is not None and grand_avg and grand_avg > 0:
            per_month_pct[cat] = 100.0 * (avg / grand_avg)
        else:
            per_month_pct[cat] = None

    # Column widths
    categories = sorted(totals.keys())
    w_cat = max(len(cat_header), *(len(c) for c in categories)) if categories else len(cat_header)
    w_tot = max(len(tot_header), *(len(str(totals[c])) for c in categories)) if categories else len(tot_header)
    w_avg = max(len(permo_header), *(len(f"{per_month[c]:.2f}") if per_month[c] is not None else 3 for c in categories))  # 'n/a' len=3
    w_pct = max(len(perc_header), *(len(f"{per_month_pct[c]:.2f}%") if per_month_pct[c] is not None else 4 for c in categories))  # 'n/a%' len=4

    # Print header row
    print(f"{cat_header:<{w_cat}}  {tot_header:>{w_tot}}  {permo_header:>{w_avg}}  {perc_header:>{w_pct}}")
    print(f"{'-'*w_cat}  {'-'*w_tot}  {'-'*w_avg}  {'-'*w_pct}")

    # Rows
    for cat in categories:
        total = totals[cat]
        avg_str = f"{per_month[cat]:.2f}" if per_month[cat] is not None else "n/a"
        pct_str = f"{per_month_pct[cat]:.2f}%" if per_month_pct[cat] is not None else "n/a%"
        print(f"{cat:<{w_cat}}  {total:>{w_tot}}  {avg_str:>{w_avg}}  {pct_str:>{w_pct}}")

    # Totals row
    total_avg_str = f"{grand_avg:.2f}" if grand_avg is not None else "n/a"
    total_pct_str = "100.00%" if grand_avg is not None else "n/a%"
    print(f"{'-'*(w_cat + w_tot + w_avg + w_pct + 6)}")
    print(f"{'TOTAL':<{w_cat}}  {grand_total:>{w_tot}}  {total_avg_str:>{w_avg}}  {total_pct_str:>{w_pct}}")

def main():
    args = parse_args()
    folder = Path(args.dir)
    if not folder.exists() or not folder.is_dir():
        print(f"❌ Directory not found: {folder}")
        return

    json_files = sorted(folder.glob("*.json"))
    if not json_files:
        print(f"⚠️  No JSON files found in: {folder}")
        return

    for jf in json_files:
        try:
            summary = summarize_file(jf)
            print_repo_summary(summary)
        except Exception as e:
            print(f"\n=== {jf.stem} ===")
            print(f"Error processing file: {e}")

if __name__ == "__main__":
    main()
