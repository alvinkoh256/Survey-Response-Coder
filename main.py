import argparse
import pandas as pd
from src.utils import load_questions_config
from src.categoriser import run_categorisation_for_question

def parse_args():
    ap = argparse.ArgumentParser(description="Batch-categorise survey responses with Pandas + LLM API.")
    ap.add_argument("--input", required=True, help="Path to input CSV/Excel.")
    ap.add_argument("--output", required=True, help="Path to output CSV (will be overwritten atomically).")
    ap.add_argument("--config", required=True, help="Path to questions_config.json.")
    ap.add_argument("--model", default="azure~openai.gpt-4o-mini", help="LLM model id for the API.")
    ap.add_argument("--batch-size", type=int, default=1, help="How many rows to send per request (default 1).")
    ap.add_argument("--no-verbose", action="store_true", help="Disable per-row console logs.")
    return ap.parse_args()

def load_df(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)

if __name__ == "__main__":
    args = parse_args()
    df = load_df(args.input)
    q_specs = load_questions_config(args.config)

    for spec in q_specs:
        q_col = spec["question_col"]
        instr = spec["instruction"]
        if q_col not in df.columns:
            print(f"⚠️  Skipping missing column: {q_col}")
            continue

        print(f"→ Processing: {q_col}")
        new_col = run_categorisation_for_question(
            df,
            q_col,
            instr,
            model=args.model,
            output_path=args.output,
            autosave_every_pass=True,
            batch_size=max(1, args.batch_size),
            verbose=not args.no_verbose,
        )
        print(f"   Created/filled: {new_col}")

    df.to_csv(args.output, index=False)
    print(f"✅ Done. Saved to {args.output}")
