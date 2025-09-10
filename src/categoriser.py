from __future__ import annotations
import json
from collections import OrderedDict
import pandas as pd

from src.api_client import create_chat, send_message
from src.utils import make_content, make_batch_content, atomic_save_df

CACHE_FILE = "categories_cache.json"

def _empty(x) -> bool:
    return (pd.isna(x)) or (isinstance(x, str) and x.strip() == "")

def _parse_labels(s: str) -> list[str]:
    if _empty(s):
        return []
    return [t.strip() for t in str(s).split(";") if t.strip()]

def _seed_categories_from_df(df: pd.DataFrame, code_col_idx: int) -> list[str]:
    """Collect labels present in the codes col so far (dedupe, preserve order)."""
    seen = OrderedDict()
    col = df.iloc[:, code_col_idx]
    for v in col:
        for lab in _parse_labels(v):
            if lab not in seen:
                seen[lab] = None
    return list(seen.keys())

def _load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _safe_new_col_name(df: pd.DataFrame, base_name: str) -> str:
    """Ensure new column name is unique (e.g., '...[Codes]', '...[Codes] (2)')."""
    name = base_name
    i = 2
    while name in df.columns:
        name = f"{base_name} ({i})"
        i += 1
    return name

def _insert_codes_column_right_of(df: pd.DataFrame, question_col: str, suffix=" [Codes]") -> tuple[str, int]:
    if question_col not in df.columns:
        raise KeyError(f"Question column not found: {question_col}")
    q_idx = df.columns.get_loc(question_col)
    new_col_base = f"{question_col}{suffix}"
    new_col = _safe_new_col_name(df, new_col_base)
    df.insert(loc=q_idx + 1, column=new_col, value="")
    return new_col, q_idx + 1

def _find_codes_columns(df: pd.DataFrame, question_col: str, suffix=" [Codes]") -> list[str]:
    base = f"{question_col}{suffix}"
    return [c for c in df.columns if c == base or c.startswith(base + " (")]

def get_or_create_codes_column(df: pd.DataFrame, question_col: str, suffix=" [Codes]") -> tuple[str, int, bool]:
    """Reuse rightmost existing Codes col if present, else create a new one."""
    codes_cols = _find_codes_columns(df, question_col, suffix=suffix)
    if codes_cols:
        codes_col = max(codes_cols, key=lambda c: df.columns.get_loc(c))
        return codes_col, df.columns.get_loc(codes_col), False
    new_col, idx = _insert_codes_column_right_of(df, question_col, suffix=suffix)
    return new_col, idx, True

def _blank_row_indices(df: pd.DataFrame, col_idx: int) -> list[int]:
    return [int(i) for i in df.index if _empty(df.iat[i, col_idx])]

def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def run_categorisation_for_question(
    df: pd.DataFrame,
    question_col: str,
    instruction: str,
    *,
    model: str = "azure~openai.gpt-4o-mini",
    output_path: str | None = None,
    autosave_every_pass: bool = True,
    batch_size: int = 1,                    # <-- NEW
    verbose: bool = True,                   # <-- optional prints
) -> str:
    # get/create [Codes] column to the right
    codes_col_name, codes_col_idx, _created = get_or_create_codes_column(df, question_col, suffix=" [Codes]")

    cache_key = question_col
    cache = _load_cache()
    categories = _seed_categories_from_df(df, codes_col_idx)
    for c in cache.get(cache_key, []):
        if c not in categories:
            categories.append(c)

    def _has_blanks() -> bool:
        return any(_empty(v) for v in df.iloc[:, codes_col_idx])

    while _has_blanks():
        chat_id = create_chat(model=model, name=f"coding:{question_col}")

        # refresh category seed each pass
        seeded = _seed_categories_from_df(df, codes_col_idx)
        for c in seeded:
            if c not in categories:
                categories.append(c)

        try:
            # Work over BLANK rows only, in batches
            blanks = _blank_row_indices(df, codes_col_idx)
            for group in _chunks(blanks, max(1, batch_size)):
                if batch_size == 1:
                    # ----- single-row path (legacy) -----
                    row_idx = group[0]
                    ans = "" if pd.isna(df.at[row_idx, question_col]) else str(df.at[row_idx, question_col])
                    content_str = make_content(instruction, question_col, ans, categories)
                    resp = send_message(
                        chat_id,
                        content_str,
                        streaming=False,
                        cloak=True,
                        params={"temperature": 0},
                        properties={"source": "pandas-llm-batch-categoriser"},
                    )
                    response = (resp.get("response", {}) or {}).get("content", "")
                    try:
                        obj = json.loads(response) if str(response).strip().startswith("{") else {"categories": str(response).strip()}
                        cat_str = str(obj.get("categories", "")).strip()
                    except Exception:
                        cat_str = str(response).strip()

                    # 🔹 Clean up any "NEW:" prefixes before saving
                    cat_str = "; ".join([c.strip().removeprefix("NEW:").strip() for c in cat_str.split(";") if c.strip()])

                    # write cleaned string back into DataFrame
                    df.iat[row_idx, codes_col_idx] = cat_str

                    # update categories list
                    for c in _parse_labels(cat_str):
                        if c not in categories:
                            categories.append(c)


                    if verbose:
                        print("\n----------------------")
                        print(f"Q: {question_col}")
                        print(f"Row: {row_idx}")
                        print(f"A: {ans}")
                        print(f"LLM: {cat_str}")
                        print("----------------------\n")

                else:
                    # ----- batched path -----
                    items = []
                    for r in group:
                        a = "" if pd.isna(df.at[r, question_col]) else str(df.at[r, question_col])
                        items.append({"row": int(r), "answer": a})

                    content_str = make_batch_content(instruction, question_col, items, categories)
                    resp = send_message(
                        chat_id,
                        content_str,
                        streaming=False,
                        cloak=True,
                        params={"temperature": 0},
                        properties={"source": "pandas-llm-batch-categoriser"},
                    )
                    raw = (resp.get("response", {}) or {}).get("content", "").strip()

                    # Parse strict JSON: {"results":[{"row":<int>, "categories":"..."}]}
                    results = []
                    try:
                        parsed = json.loads(raw)
                        results = parsed.get("results", [])
                    except Exception:
                        # Fallback: try to detect a JSON list directly
                        try:
                            maybe_list = json.loads(raw)
                            if isinstance(maybe_list, list):
                                results = maybe_list
                        except Exception:
                            # Last resort: treat the whole batch as one string (not ideal)
                            results = [{"row": it["row"], "categories": str(raw)} for it in items]

                    # Write back results
                    for res in results:
                        try:
                            r = int(res["row"])
                            cat_str = str(res.get("categories", "")).strip()
                        except Exception:
                            continue
                        if r in group:
                            df.iat[r, codes_col_idx] = cat_str
                            for c in _parse_labels(cat_str):
                                if c not in categories:
                                    categories.append(c)

                            if verbose:
                                ans = "" if pd.isna(df.at[r, question_col]) else str(df.at[r, question_col])
                                print("\n----------------------")
                                print(f"Q: {question_col}")
                                print(f"Row: {r}")
                                print(f"A: {ans}")
                                print(f"LLM: {cat_str}")
                                print("----------------------\n")

        except Exception as e:
            # persist on failure then retry pass
            cache[cache_key] = categories
            _save_cache(cache)
            if output_path:
                atomic_save_df(df, output_path)
            print(f"[pass aborted for '{question_col}'] {e} — restarting pass...")
            continue

        # end of pass
        if autosave_every_pass and output_path:
            atomic_save_df(df, output_path)

    # final persist
    cache[cache_key] = categories
    _save_cache(cache)
    if output_path:
        atomic_save_df(df, output_path)

    return codes_col_name
