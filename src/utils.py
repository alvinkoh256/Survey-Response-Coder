import os
import re
import json
import math
import tempfile
import pandas as pd

_ZW = re.compile(r"[\u200B-\u200D\u2060\uFEFF]")  # zero-width/format chars

def atomic_save_df(df: pd.DataFrame, path: str):
    """Atomic write so you never leave a half-written CSV."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    os.close(fd)
    try:
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

def make_content(instructions: str, question: str, answer, categories: list[str]) -> str:
    if answer is None or (isinstance(answer, float) and math.isnan(answer)):
        ans = ""
    else:
        ans = str(answer)

    # normalize quotes, spaces, strip zero-width & non-printables
    ans = (ans.replace("\u2019", "'").replace("\u2018", "'")
              .replace("\u201c", '"').replace("\u201d", '"')
              .replace("\u00A0", " "))
    ans = _ZW.sub("", ans)
    ans = "".join(ch for ch in ans if ch.isprintable())

    return json.dumps(
        {"instructions": str(instructions), "question": str(question), "answer": ans, "categories": list(categories)},
        ensure_ascii=True,
        separators=(",", ":"),
    )

def load_questions_config(path_or_list):
    """Accept either a path to JSON config or a Python list of dicts."""
    if isinstance(path_or_list, str):
        with open(path_or_list, "r", encoding="utf-8") as f:
            return json.load(f)
    return path_or_list

def make_batch_content(instructions: str, question: str, items: list[dict], categories: list[str]) -> str:
    """
    items = [{"row": <int>, "answer": <str>}]
    Returns a JSON string instructing the model to ONLY reply with:
      {"results":[{"row":<int>,"categories":"Label1; Label2"}]}
    """
    # sanitize answers
    def _clean(a):
        if a is None or (isinstance(a, float) and math.isnan(a)):
            a = ""
        a = str(a)
        a = (a.replace("\u2019", "'").replace("\u2018", "'")
               .replace("\u201c", '"').replace("\u201d", '"')
               .replace("\u00A0", " "))
        a = _ZW.sub("", a)
        a = "".join(ch for ch in a if ch.isprintable())
        return a

    clean_items = [{"row": it["row"], "answer": _clean(it.get("answer", ""))} for it in items]

    payload = {
        "instructions": str(instructions),
        "question": str(question),
        "categories": list(categories),
        "items": clean_items,
        # Strong spec so output is parseable
        "output_spec": (
            "Reply ONLY with JSON: "
            "{\"results\":[{\"row\":<int>,\"categories\":\"Label1; Label2\"}, ...]}"
            " — no prose, no markdown, no extra keys."
        )
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
