# Call Screen evaluation data

## `call-screen-simulated-v1`

`data/call-screen-simulated-v1.jsonl` contains **10,000 distinct simulated caller turns**. It is a reproducible, stratified corpus for testing the Call Screen classifier and decision policy before any live-policy test.

- 4,000 harmful calls across eight scam families
- 4,000 normal calls across eight ordinary calling families
- 2,000 unclear calls across four ambiguous calling families
- 7,000 development, 1,500 validation, and 1,500 held-out records

Each row records the caller transcript, scenario label, expected policy decision, scam/normal/unclear family, and split. The manifest records the fixed random seed and SHA-256 hash.

This corpus is **simulated**, not real calling traffic. Its labels are assigned by the scenario definition; it has no customer data, Twilio calls, Gemini results, or experiment outcomes. It supports offline recall, false-block rate, decision accuracy, latency, and threshold analysis. Its stratified prevalence means measured precision is an evaluation measure, not production precision.

Regenerate it without network or API use:

```powershell
backend\.venv\Scripts\python evaluation\generate_call_set.py
```

Check the 10,000-call corpus without calling Gemini:

```powershell
backend\.venv\Scripts\python evaluation\run.py --dataset evaluation\data\call-screen-simulated-v1.jsonl --split all --limit 3
```

## First baseline run

`prepare_baseline_sample.py` creates a fixed 1,000-call development sample:

- 400 harmful calls
- 400 normal calls
- 200 unclear calls

Create or recreate it without network or API use:

```powershell
backend\.venv\Scripts\python evaluation\prepare_baseline_sample.py
```

Check the prepared run without Gemini:

```powershell
backend\.venv\Scripts\python evaluation\run.py --dataset evaluation\data\baseline-development-1000.jsonl --split development --limit 25
```

The command reports the separate result path it would use under `evaluation/runs/`; it never overwrites the web demo's `results.json` fixture. `--run` makes Gemini requests and writes results. Do not add it without explicitly deciding on the batch size and cost. The 1,000-call baseline can be run in resumable batches, such as 25 calls at a time. A 10,000-call Gemini run should never be started by default.

## Existing 18-call pilot

`cases.json` and `results.json` remain the small simulated fixture used by the current web demo. They show the interaction and evaluation layout only. They are not a claim of Gemini model quality.
