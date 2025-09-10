#!/usr/bin/env python
import argparse
import pandas as pd

# ---- Edit this alias map to collapse near-duplicates across ALL coded columns ----
# keys are lowercased variants -> unified label
ALIAS_MAP = {
    "phishing prevention": "Phishing/Scam Prevention",
    "scam prevention": "Phishing/Scam Prevention",
    "phishing/scam prevention": "Phishing/Scam Prevention",
    "two factor authentication": "Two-Factor Authentication",
    "2fa": "Two-Factor Authentication",
    "passwords": "Password Management",
    "strong passwords": "Password Management",
    "privacy": "Privacy Protection",
    "privacy protection": "Privacy Protection",
    "scam awareness": "Scam Awareness",
    "nil": "NIL",
    "none": "NIL",
    "na": "NIL",
    "n/a": "NIL",
}

def tidy_cell(val: str | float | None) -> str | float | None:
    """Deduplicate within a cell and collapse aliases -> unified labels."""
    if pd.isna(val):
        return val
    parts = [p.strip() for p in str(val).split(";") if p.strip()]
    out, seen = [], set()
    for p in parts:
        key = p.casefold()
        unified = ALIAS_MAP.get(key, None)
        label = unified or p
        if label not in seen:
            out.append(label)
            seen.add(label)
    return "; ".join(out)

def summarise_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Return Category/Count/% for one coded column (based on total rows)."""
    # in-place tidy for this view (does not modify df on disk)
    series = df[col].map(tidy_cell)
    # explode labels
    split = (
        series.dropna()
              .astype(str)
              .str.split(";")
    )
    labels = [
        lab.strip()
        for sub in split
        for lab in sub
        if lab.strip()
    ]
    if not labels:
        return pd.DataFrame(columns=["Category", "Count", "%"])
    counts = pd.Series(labels).value_counts()
    out = counts.reset_index()
    out.columns = ["Category", "Count"]
    total = len(df) if len(df) > 0 else 1
    out["%"] = (out["Count"] / total * 100).round(2)
    return out

def find_coded_columns(df: pd.DataFrame) -> list[str]:
    """Pick columns that look like LLM-coded outputs."""
    return [c for c in df.columns if "[Codes]" in c or "Code for:" in c]

def main():
    ap = argparse.ArgumentParser(description="Summarise coded survey columns (Category, Count, %).")
    ap.add_argument("--input", required=True, help="Path to coded CSV/Excel.")
    ap.add_argument("--sheet", default=None, help="Excel sheet name (if XLSX).")
    ap.add_argument("--save-csv", default=None, help="Optional: path to save combined summary CSV.")
    args = ap.parse_args()

    # Load
    if args.input.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.input, sheet_name=args.sheet)
    else:
        df = pd.read_csv(args.input)

    coded_cols = find_coded_columns(df)
    if not coded_cols:
        print("No coded columns found. (Look for headers containing '[Codes]' or 'Code for:')")
        return

    all_blocks = []
    print(f"\nFound {len(coded_cols)} coded column(s):")
    for c in coded_cols:
        print(f"  • {c}")
    print()

    for col in coded_cols:
        summary = summarise_column(df, col)
        print(f"===== {col} =====")
        if summary.empty:
            print("(no labels)")
            print()
            continue
        print(summary.to_string(index=False))
        print()
        # for optional combined export
        tmp = summary.copy()
        tmp.insert(0, "Question", col)
        all_blocks.append(tmp)

    if args.save_csv and all_blocks:
        combined = pd.concat(all_blocks, ignore_index=True)
        combined.to_csv(args.save_csv, index=False)
        print(f"Saved combined summary to: {args.save_csv}")

if __name__ == "__main__":
    main()
