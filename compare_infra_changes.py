#!/usr/bin/env python3
"""
compare_infra_changes.py

Compare how large Infrastructure changes are (in lines_changed) vs other categories
for each JSON in a folder (default: repo_data). Optionally normalize by months.

Assumes each JSON has shape:
{
  "<sha>": {
    "Date": "YYYY-MM-DDTHH:MM:SSZ",
    "Files": [
      {"filename": "...", "lines_changed": <int>, "category": "Development" | "Test" | "Build" | "Infrastructure" | ...},
      ...
    ]
  },
  ...
}

Usage:
  python compare_infra_changes.py
  python compare_infra_changes.py --dir repo_data --per-month --csv infra_comparison.csv
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import csv
import math
import statistics

MEAN_DAYS_PER_MONTH = 30.4375  # 365.25 / 12
CANONICAL = ["Development", "Build", "Infrastructure", "Test", "Others", "Uncategorized"]

def parse_args():
    ap = argparse.ArgumentParser(description="Compare Infrastructure lines_changed vs other categories across JSON repos.")
    ap.add_argument("--dir", "-d", default="repo_data", help="Directory of *.json files (default: repo_data)")
    ap.add_argument("--per-month", action="store_true",
                    help="Normalize category totals by repository age in months (earliest..latest commit)")
    ap.add_argument("--csv", "-o", default=None, help="Optional path to write a CSV with the results")
    return ap.parse_args()

def parse_iso8601_z(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def normalize_category(cat) -> str:
    if cat is None:
        return "Uncategorized"
    c = str(cat).strip().lower()
    if c in {"dev", "development"}:
        return "Development"
    if c in {"build", "config", "configuration"}:
        return "Build"
    if c in {"infra", "infrastructure", "ops", "ci", "cd"}:
        return "Infrastructure"
    if c in {"test", "tests", "qa"}:
        return "Test"
    if c in {"other", "others", "misc", "unknown"}:
        return "Others"
    return c.title() if c else "Uncategorized"

def to_int(x) -> int:
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return 0

def load_repo(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Tally lines per category and collect dates
    tallies = defaultdict(int)
    dates = []
    commit_count = 0

    for _sha, obj in (data or {}).items():
        if not isinstance(obj, dict):
            continue
        ds = obj.get("Date")
        if ds:
            try:
                dates.append(parse_iso8601_z(ds))
            except Exception:
                pass
        files = obj.get("Files") or []
        for f in files:
            if not isinstance(f, dict):
                continue
            cat = normalize_category(f.get("category"))
            tallies[cat] += to_int(f.get("lines_changed", 0))
        commit_count += 1

    # Ensure canonical keys exist
    for k in CANONICAL:
        tallies.setdefault(k, 0)

    # Compute age in months if needed
    if dates:
        earliest = min(dates)
        latest = max(dates)
        age_days = (latest - earliest).days
        age_months = (age_days / MEAN_DAYS_PER_MONTH) if age_days > 0 else 0.0
        earliest_s = earliest.date().isoformat()
        latest_s = latest.date().isoformat()
    else:
        earliest_s = latest_s = ""
        age_days = 0
        age_months = 0.0

    return {
        "repo": json_path.stem,
        "earliest": earliest_s,
        "latest": latest_s,
        "age_days": age_days,
        "age_months": age_months,
        "commit_count": commit_count,
        "tallies": dict(tallies)
    }

def ratios(infra: float, other: float):
    if other == 0:
        return math.inf if infra > 0 else 0.0
    return infra / other

def fmt_ratio(x: float) -> str:
    if x == math.inf:
        return "∞"
    return f"{x:.2f}"

def main():
    args = parse_args()
    folder = Path(args.dir)
    if not folder.exists() or not folder.is_dir():
        print(f"❌ Directory not found: {folder}")
        return

    files = sorted(folder.glob("*.json"))
    if not files:
        print(f"⚠️  No JSON files found in {folder}")
        return

    rows = []
    # For cross-repo stats
    infra_shares = []
    infra_vs_dev = []
    infra_vs_build = []
    infra_vs_test = []
    infra_vs_others = []

    for path in files:
        repo = load_repo(path)

        tallies = repo["tallies"].copy()

        # Optionally normalize by months
        if args.per_month:
            m = repo["age_months"]
            if m > 0:
                for k in tallies:
                    tallies[k] = tallies[k] / m

        total = sum(tallies.values())
        infra = tallies.get("Infrastructure", 0.0)
        dev = tallies.get("Development", 0.0)
        bld = tallies.get("Build", 0.0)
        tst = tallies.get("Test", 0.0)
        oth = tallies.get("Others", 0.0) + tallies.get("Uncategorized", 0.0)

        share = (100.0 * infra / total) if total > 0 else 0.0

        r_dev = ratios(infra, dev)
        r_bld = ratios(infra, bld)
        r_tst = ratios(infra, tst)
        r_oth = ratios(infra, oth)

        rows.append({
            "repo": repo["repo"],
            "earliest": repo["earliest"],
            "latest": repo["latest"],
            "age_months": round(repo["age_months"], 2),
            "metric_base": "per_month" if args.per_month else "total_lines",
            "Infrastructure": infra,
            "Development": dev,
            "Build": bld,
            "Test": tst,
            "Others+Uncat": oth,
            "TOTAL": total,
            "Infra_share_%": share,
            "Infra/Dev": r_dev,
            "Infra/Build": r_bld,
            "Infra/Test": r_tst,
            "Infra/Others": r_oth
        })

        if total > 0:
            infra_shares.append(share)
        if dev > 0:   infra_vs_dev.append(infra / dev)
        if bld > 0:   infra_vs_build.append(infra / bld)
        if tst > 0:   infra_vs_test.append(infra / tst)
        if oth > 0:   infra_vs_others.append(infra / oth)

    # Print table
    headers = ["repo","metric_base","Infrastructure","Development","Build","Test","Others+Uncat","TOTAL","Infra_share_%","Infra/Dev","Infra/Build","Infra/Test","Infra/Others"]
    str_rows = []
    for r in rows:
        str_rows.append([
            r["repo"],
            r["metric_base"],
            f"{r['Infrastructure']:.2f}" if isinstance(r["Infrastructure"], float) else str(r["Infrastructure"]),
            f"{r['Development']:.2f}" if isinstance(r["Development"], float) else str(r["Development"]),
            f"{r['Build']:.2f}" if isinstance(r["Build"], float) else str(r["Build"]),
            f"{r['Test']:.2f}" if isinstance(r["Test"], float) else str(r["Test"]),
            f"{r['Others+Uncat']:.2f}" if isinstance(r["Others+Uncat"], float) else str(r["Others+Uncat"]),
            f"{r['TOTAL']:.2f}" if isinstance(r["TOTAL"], float) else str(r["TOTAL"]),
            f"{r['Infra_share_%']:.2f}%",
            fmt_ratio(r["Infra/Dev"]),
            fmt_ratio(r["Infra/Build"]),
            fmt_ratio(r["Infra/Test"]),
            fmt_ratio(r["Infra/Others"]),
        ])

    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(vals):
        return "  ".join(str(vals[i]).ljust(widths[i]) if i in (0,1) else str(vals[i]).rjust(widths[i]) for i in range(len(vals)))

    print("\nInfrastructure vs Other Categories ({}):".format("Avg per Month" if args.per_month else "Totals"))
    print(fmt_row(headers))
    print(fmt_row(["-"*w for w in widths]))
    for row in str_rows:
        print(fmt_row(row))

    # Cross-repo summary
    def safe_stats(a):
        return {
            "count": len(a),
            "mean": round(statistics.mean(a), 2) if a else "n/a",
            "median": round(statistics.median(a), 2) if a else "n/a"
        }

    print("\n-- Cross-Repo Summary --")
    print(f"Infrastructure share of total (%)    -> n={len(infra_shares)}  mean={safe_stats(infra_shares)['mean']}  median={safe_stats(infra_shares)['median']}")
    print(f"Infra/Dev ratio                      -> n={len(infra_vs_dev)}  mean={safe_stats(infra_vs_dev)['mean']}  median={safe_stats(infra_vs_dev)['median']}")
    print(f"Infra/Build ratio                    -> n={len(infra_vs_build)}  mean={safe_stats(infra_vs_build)['mean']}  median={safe_stats(infra_vs_build)['median']}")
    print(f"Infra/Test ratio                     -> n={len(infra_vs_test)}  mean={safe_stats(infra_vs_test)['mean']}  median={safe_stats(infra_vs_test)['median']}")
    print(f"Infra/Others ratio                   -> n={len(infra_vs_others)}  mean={safe_stats(infra_vs_others)['mean']}  median={safe_stats(infra_vs_others)['median']}")

    if args.csv:
        out = Path(args.csv)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers + ["earliest","latest","age_months"])
            for r in rows:
                w.writerow([
                    r["repo"], r["metric_base"], r["Infrastructure"], r["Development"], r["Build"], r["Test"], r["Others+Uncat"], r["TOTAL"],
                    round(r["Infra_share_%"], 4), r["Infra/Dev"], r["Infra/Build"], r["Infra/Test"], r["Infra/Others"],
                    r["earliest"], r["latest"], round(r["age_months"], 2)
                ])
        print(f"\n💾 Wrote CSV to: {out.resolve()}")

if __name__ == "__main__":
    main()
