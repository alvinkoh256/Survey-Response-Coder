Right now your README intro is clear, but it reads like **documentation** more than a **value pitch**. To “sell” the project better (whether to employers, collaborators, or users), you want to emphasise **pain → solution → impact → credibility**.

Here’s a tightened and more compelling rewrite:

---

# 📊 Survey Response Coder (Pandas + LLM API)

A lightweight, production-ready tool to **turn messy free-text survey responses into structured insights**, powered by Pandas and the [AIBOTS Gov](https://uat.aibots.gov.sg) LLM API.

---

## ❗ Problem

Organisations rely on open-ended survey questions to understand people’s concerns, behaviours, and experiences. But analysing them is a nightmare:

* **Slow:** thousands of responses can take weeks to manually read and code.
* **Inconsistent:** different analysts apply categories differently, leading to bias.
* **Unscalable:** insights arrive too late to influence fast-moving decisions.

---

## 💡 Solution

**Survey Response Coder** automates this process end-to-end:

* 🤖 **AI-powered categorisation** — Uses AIBOTS Gov’s LLM to classify responses with high accuracy.
* ⚡ **Batch processing** — Analyse responses 10× faster by coding rows in configurable chunks.
* 📝 **Smart output** — Adds a `[Codes]` column directly beside each question for easy tracking.
* 🔄 **Continuous autosave** — Resume safely even if the process stops mid-run.
* 🗂️ **Reusable workflows** — Configurable `questions_config.json` lets you plug in new surveys instantly.

**Outcome:** What once took **hours or days of manual coding** now takes **minutes**, producing **consistent, human-interpretable categories** ready for analysis.

## 🔑 Pre-requisites

Before running the tool, prepare these:

1. **Eligibility**

   * You must be a **Singapore Government employee** with a valid **WOG email address** to obtain an AIBOTS Gov API key.
   * This tool will not work without proper access.

2. **Survey data file**

   * A CSV or Excel file containing your survey responses.
   * Each **open-ended question** must be in its own column (header).
   * Closed-ended or demographic questions can remain in the file — the tool only processes the columns you configure.

3. **API key**

   * Obtain an API key from [AIBOTS Gov](https://uat.aibots.gov.sg).
   * Export it into your environment:

     ```powershell
     $env:AIBOTS_API_KEY = "your-real-key-here"
     ```

     Or save it in a `.env` file:

     ```
     AIBOTS_API_KEY=your-real-key-here
     ```

4. **Categorisation instructions**

   * For each **survey question (column header)** you want to process, write **one instruction** that tells the LLM how to categorise all answers in that column.
   * Example:

     * *“Categorise into Phishing, Malware, Identity Theft. Use 1–3 labels max.”*
     * *“Categorise into Privacy Protection, Scam Awareness, or NIL if no answer.”*

5. **Batch size preference**

   * Choose how many responses to process at once.
   * Default = `1` (safe but slower). Example: `--batch-size 10` for 10 rows per API call.

---

## ⚡ Usage

### 1. Configure your questions

Create a `questions_config.json` file describing **which columns to code** and **how to categorise them**.

Example:

```json
[
  {
    "question_col": "What worries you most when you use your mobile devices or the internet?",
    "instruction": "Categorise answers into Phishing, Scam Awareness, Malware, or NIL if no answer."
  },
  {
    "question_col": "How do you try to stay safe online?",
    "instruction": "Categorise answers into Privacy Protection, Scam Prevention, Strong Passwords, or NIL."
  }
]
```

⚠️ Important:

* `question_col` must **exactly match** the column header in your survey file.
* `instruction` applies to **all answers in that column**, not per row.

---

### 2. Run the script

⚠️ **Important:**
To allow the script to save progress (persistent writes to the `[Codes]` columns), your `--input` and `--output` must point to the **same file**.

**Best practice:**

* Keep an untouched copy of your original survey (e.g., `Book1_original.csv`).
* Create a working copy (e.g., `Book1.csv`) and run the tool on that file.

Refer to [📥 Input CSV format](#-input-csv-format) to understand the structure of your survey file.

**Single row at a time (default):**

```bash
python main.py --input Book1.csv --output Book1.csv --config questions_config.json
```

**Batch mode (faster):**

```bash
python main.py --input Book1.csv --output Book1.csv --config questions_config.json --batch-size 10
```

**Quiet mode (no row-by-row logs):**

```bash
python main.py --input Book1.csv --output Book1.csv --config questions_config.json --batch-size 10 --no-verbose
```

---

## 📥 Input CSV format

Your survey file should be a **CSV (or Excel)** with each **open-ended question as a column header**, and each row as a respondent’s answer.

Example (`Book1.csv`):

| What does 'digital safety' mean to you? How do you protect yourself or stay safe in online spaces? | What digital threats are you most concerned about when going online? | What challenges do you face when trying to stay safe online or protecting yourself from digital threats? |
| -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Not giving out personal info                                                                       | Phishing emails                                                      | Hard to tell if websites are real                                                                        |
| Using strong passwords                                                                             | Malware, viruses                                                     | Too many scam messages                                                                                   |
| Being careful of links                                                                             | Identity theft                                                       | Don’t know enough about online safety                                                                    |

---

## 📤 Output CSV format

After running the tool, a new `[Codes]` column will appear immediately **to the right of each question** with the categorisation labels from the LLM:

| What does 'digital safety' mean to you? How do you protect yourself or stay safe in online spaces? | What does 'digital safety'... \[Codes] | What digital threats are you most concerned about when going online? | What digital threats... \[Codes] |
| -------------------------------------------------------------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------- | -------------------------------- |
| Not giving out personal info                                                                       | Privacy Protection                     | Phishing emails                                                      | Phishing                         |
| Using strong passwords                                                                             | Password Management                    | Malware, viruses                                                     | Malware                          |
| Being careful of links                                                                             | Scam Awareness                         | Identity theft                                                       | Identity Theft                   |

---

## ✅ Features

* Automates open-ended survey coding
* Config-driven (`questions_config.json`)
* Batch mode for speed
* Safe autosaving (persistent progress with same input/output file)
* Works with CSV/Excel

Perfect 👍 let’s extend your README with a new section explaining the **categories cache**. This will help users understand why their labels “stick” across runs and why they shouldn’t delete the file unless they want to reset.

Here’s the updated block you can add right after **✅ Features**:

---

## 🗂️ Categories Cache (`categories_cache.json`)

When you run the tool, it automatically maintains a **categories cache** in a file called `categories_cache.json`.

### 🔹 What it does

* Stores the list of categories discovered for each survey question (column).
* Ensures new categories added in one run are remembered in future runs.
* Prevents the model from “forgetting” previously assigned labels when you stop and restart the script.

### 🔹 How it works

* Each survey question (by column name) gets its own entry in the cache.
* After each pass, newly discovered categories are merged into the cache.
* The cache is reloaded every time you restart, so you can safely resume coding without losing progress.

### 🔹 Example

`categories_cache.json`:

```json
{
  "What digital threats are you most concerned about when going online?": [
    "Phishing",
    "Malware",
    "Identity Theft"
  ],
  "How do you try to stay safe online?": [
    "Password Management",
    "Two-Factor Authentication",
    "Privacy Protection"
  ]
}
```

### 🔹 Tips

* **Keep this file** between runs to preserve category memory.
* If you want to **start fresh** (ignore all old categories), simply delete `categories_cache.json`.
* You can also open it to quickly inspect what categories the model has generated so far.


Nice 👍 let’s add a **Summarising Results** section to the README. This will show users how to run your summariser script and what kind of output they’ll get. Here’s the block you can drop in after the **🗂️ Categories Cache** section:

---

## 📊 Summarising Results

Once your survey responses have been coded, you can quickly analyse the results with the included summariser script.

### 🔹 What it does

* Detects all `[Codes]` columns in your coded CSV/Excel file.
* Cleans duplicates and normalises label variants (e.g., *“Phishing Prevention”*, *“Scam Prevention”* → **Phishing/Scam Prevention**).
* Counts how many times each category appears.
* Shows percentages relative to the total number of survey respondents.
* Optionally exports a combined summary CSV.

### 🔹 Run it

From your project root:

```bash
python scripts/summarise_codes.py --input Book1.csv --save-csv coded_summary.csv
```

### 🔹 Example Output

```
Found 2 coded column(s):
  • What does 'digital safety' mean to you? How do you protect yourself or stay safe in online spaces? [Codes]
  • What digital threats are you most concerned about when going online? [Codes]

===== What does 'digital safety' mean to you? ... [Codes] =====
          Category  Count     %
Privacy Protection      15  30.00
Scam Awareness          10  20.00
Password Management      8  16.00
Two-Factor Authentication 5  10.00
NIL                      12  24.00

===== What digital threats are you most concerned about ... [Codes] =====
   Category  Count     %
   Phishing     25  50.00
    Malware     15  30.00
Identity Theft  10  20.00
```

### 🔹 Where to adjust

* **Which file to summarise:** set with `--input`
* **Save summary CSV:** set with `--save-csv coded_summary.csv`
* **Alias normalisation:** edit the `ALIAS_MAP` in `scripts/summarise_codes.py`
