# Reflection Brief — Evaluation and Observability Capstone

**Name:** Radhakrishnan
**Date:** 2026-10-18

> Ground every answer in your own run. When a question asks for a number, file name, or line, paste
> it from your artifacts — a reviewer should be able to find it. Answers that are correct in the
> abstract but cite nothing do not meet the bar. Keep it short and specific.

---

## 0. Environment

| Field | Value |
|---|---|
| OS & version | Windows 11 Home Single Language 10.0.26300, 64-bit (`environment.txt`) |
| Python version | 3.14.7 |
| Date run | 2026-10-18 |
| Ran any system live? (which) | Yes. **System 1**: the full `pipeline` run and both perturbation `extract` runs. **System 2**: the perturbation runs plus a 3×3 live-vs-recorded drift check. Both went through the Udacity/Vocareum proxy. System 3 ran offline (`--offline`), as instructed. |

---

## 1. Validated, routed pipeline

| Evidence | Value |
|---|---|
| Passing test count | **45 passed** (`45 passed, 3 skipped`; the 3 skipped are the `live`-marked tests) — `01-policy-pipeline/tests.txt` |
| Routing output file | `01-policy-pipeline/routing_decisions.json` (9 decisions), from `pipeline-run.txt` |
| auto_approve / human_review / spot_check counts | 0 / 8 / 1  (`"auto_approve": 0`, `"human_review": 8`, `"spot_check": 1`, plus `"escalations": 1`) |

**1a. Retry boundary.** From your perturbation run (a required field removed), paste the escalation
record. How many API calls did the system make, and why is retrying a futile case worse than
escalating it?

> From `01-policy-pipeline/perturbation-run.txt` (POL-2025-006 with the premium blanked):
> ```
> "category": "missing_source",
> "detected_pattern": "premium_amount_absent",
> "field": "premium_amount",
> "kind": "escalation",
> "policy_id": "POL-2025-006",
> "reason": "Field 'premium_amount' returned null \u2014 the source document does not contain this information. Retry is futile; escalate to human review."
> ```
> **One API call.** The capture has exactly one `HTTP Request: POST .../v1/messages` line before
> `validation_failed`, and then the escalation. Retrying is worse than escalating for three reasons:
> - A retry only helps when the model can fix its own output, as with a `format` or `consistency`
>   error. A premium that isn't in the document can't be fixed by asking again.
> - Each retry pays for another call, adds latency, and holds the policy in the queue.
> - Worst of all, a retry prompt that says "premium_amount is required" pressures the model to
>   produce *some* number. That turns an honest null into a plausible invented premium that sails
>   through to auto-approve.
>
> Escalating on the first `missing_source` failure keeps the null visible and sends it to a human,
> who can actually go and get the missing page.

**1b. Reading the router.** Pick one `human_review` record from your routing output. Which of the
three signals (confidence, reviewer, integration) sent it to a human? If you had trusted the model's
confidence alone, what would have happened?

> POL-2025-002 in `routing_decisions.json`:
> `"coverage_limit": 0.99`, `"deductible": 0.95`, `"endorsements": 0.95`, `"exclusions": 0.99`, `"policy_type": 0.99`, `"premium_amount": 0.99`,
> `"fields_below_threshold": []`, `"integration_failures": []`,
> `"reason": "reviewer_disagreement=['coverage_limit', 'deductible']"`.
>
> - **Which signal:** only the **independent reviewer** fired. The confidence check was clean: every
>   field was ≥ 0.95 against `DEFAULT_CONFIDENCE_THRESHOLD = 0.90`. The integration pass was clean too.
> - **Confidence alone:** this policy would have been **auto-approved**. The extractor was 0.95–0.99
>   sure of a coverage limit and deductible that a second model, reading the same document, disagreed on.
> - **The same pattern elsewhere:** POL-2025-008 (`"reason": "reviewer_disagreement=['policy_type']"`,
>   all confidences ≥ 0.95) is the fine-art floater that the extractor confidently filed under `"other"`.
>   In this live run, all 8 `human_review` decisions cite `reviewer_disagreement`.

**1c. Where the aggregate lies.** Run the calibration snippet. Quote the one cell whose accuracy lags
its confidence, plus the overall figure. What does slicing by `policy_type × field` catch that a
single number hides?

> From `01-policy-pipeline/calibration-report.txt`:
> `umbrella  exclusions      n=2 conf=0.93 acc=0.00 brier=0.865` and `OVERALL brier=0.291`.
>
> - **What the aggregate shows:** 4 of 6 labels are correct, and an overall Brier of 0.291 looks
>   mediocre but tolerable.
> - **What the slice shows:** one specific job, reading *exclusions on umbrella policies*, is wrong
>   **every time** while the model claims 93% confidence. The other cells (`auto premium_amount ...
>   acc=1.00 brier=0.003`, `home deductible ... acc=1.00 brier=0.010`) average that failure away.
> - **Why it matters:** slicing by `policy_type × field` turns "the model is mostly fine" into a
>   specific fix: lower the auto-approve threshold, or force review, for umbrella exclusions. It also
>   says where to point the spot-check sampler.

---

## 2. Schema-enforced two-pass extraction

| Evidence | Value |
|---|---|
| Passing test count | **25 passed** — `02-mortgage-extraction/tests.txt` |
| Document run | `fixtures/documents/income_sum_mismatch.txt` (`discrepancy-run.txt`); also `appraisal_informal_sqft.txt` and `income_missing_bonus.txt` (`extract-run.txt`) |
| Classified type | `type=income_verification` for the income documents and `type=appraisal` for the appraisal, from the `classify:` log lines |

**2a. Two guarantees.** Paste your discrepancy-run output. Tool use already forces valid JSON, yet the
validator still catches a bad sum. Why are these two different guarantees? Name one error each cannot
catch.

> From `02-mortgage-extraction/discrepancy-run.txt`:
> ```
> "stated_monthly_total": 10892.17
> "consistent": false,
> "field": "total_monthly_income",
> "calculated": 9642.17,
> "stated": 10892.17,
> "delta": -1250.0
> ```
> **The two guarantees:**
> - **Forced `tool_choice` with a JSON Schema guarantees shape.** The right keys and types come back,
>   and numbers are numbers.
> - **The validator guarantees meaning across fields.** The values have to agree with each other.
>   `10892.17` is a perfectly valid number in a perfectly valid object; it just isn't the sum of the
>   five line items. The $1,250 gap is the `Bonus - Performance      -            -        1,250.00` line counted twice.
>
> **What each one can't catch:**
> - **The schema can't catch** a bad sum like this one, because every field passes its type check.
> - **The validator can't catch** a value that is wrong but internally consistent. My own run has one.
>   `income_missing_bonus.txt` says `Pay Rate: $5,673.08 / bi-weekly` and `Annual Salary: $147,500.00`,
>   yet the recorded extraction puts `"base_monthly": 5673.08` (`extract-run.txt`) into a *monthly*
>   field. With no stated total to compare against, the validator reports `"consistent": true`.

**2b. Refusing to fabricate.** Run on a document missing a field. Paste that field's output. Why null
instead of an invented value? Point to the schema choice that allows it.

> From `02-mortgage-extraction/extract-run.txt` (`income_missing_bonus.txt`, a paystub with no bonus line):
> `"bonus_monthly": null,` together with `"consistent": true` and `[exit code: 0]`.
>
> - **What allows it:** the schema declares the field as a union with null,
>   `"bonus_monthly": {"type": ["number", "null"]}` (`mortgage_extractor/schema.py`). The system prompt
>   backs it up with rule 1: "Return null for any field not explicitly stated in the document. Do not
>   infer, default, or fabricate."
> - **Why null is right:** underwriting can treat null as "go get the document". An invented bonus,
>   or a default 0, would be indistinguishable from a real figure and would flow straight into the
>   debt-to-income calculation.
> - **What happens without it:** the schema also shows the opposite case. `loan` is top-level
>   `"required"` with a non-nullable `"amount": {"type": "number"}`. The appraisal never states a loan
>   amount; its only $410,000 figure is `FINAL APPRAISED VALUE`. Even so, the shipped recording reports
>   `"amount": 410000.0` under `"loan"` (`extract-run.txt`), an appraised value relabelled as a loan.
>   In my live runs the model refused to invent it and the run crashed instead
>   (`loan.amount  Input should be a valid number [type=float_type, input_value=None ...]`,
>   `live-vs-recorded.txt`). Nullable fields are what make honesty possible; without them the choice
>   is between fabricating and crashing.

**2c. Normalization.** Quote one field where the source text and extracted value differ in format
("about 2,400 sq ft" → `2400`). Why normalize at extraction time rather than downstream?

> The source `appraisal_informal_sqft.txt` says `Gross Living Area:   approximately 2,400 sq ft (above-grade finished)`.
> The extracted value is `"gross_living_area_sqft": 2400,` (`extract-run.txt`).
>
> **Why normalize at extraction time:**
> - The model is the only component that sees the surrounding context. It can tell that the 2,400
>   belongs to *gross living area*, not to the `~900 sq ft` basement, the `441 sq ft` garage, or the
>   `20,037 sq ft` lot in the same document.
> - Once the value is a typed integer, the schema can enforce it, and the validator and every
>   downstream consumer can compare it numerically without each re-parsing "approximately" and commas
>   in their own way.
> - Pushing the cleanup downstream means a free-text string travels through the system, and every
>   consumer has a chance to parse it differently.

---

## 3. Multi-source synthesis

| Evidence | Value |
|---|---|
| Passing test count | **34 passed** — `03-supply-chain/tests.txt` |
| Briefing file | `03-supply-chain/briefing.md` (full run in `investigation-run.txt`) |
| Section the conflict landed in | **Contested**: `### on_time_delivery_rate  _[2 sources, conflicting]_  ⚠️ ESCALATE` |

**3a. Annotate, don't arbitrate.** Quote one conflicting-metric pair from your briefing — both values,
sources, dates. Give one way a reader is better served by the preserved conflict than by a single
reconciled number.

> From `briefing.md`:
> `95.0 percent — supplier_audit (as of 2026-04-10)` and `78.0 percent — logistics (as of 2026-04-05)`.
>
> **Why keep both instead of reconciling:**
> - The two numbers come from different kinds of evidence. One is the supplier's own audit claim; the
>   other is computed from 50 shipment records, 39 of them `True` in `logistics.csv`.
> - A reconciled ~86.5% average would be a number *nobody measured*. It would also hide the fact that
>   the supplier says 95% while the shipment data says 78%.
> - Keeping both, with source and date, tells a buyer exactly what to do next: ask Meridian to explain
>   the 17-point gap, or audit the shipment-level data. The `⚠️ ESCALATE` routes that to a person.
>
> My perturbation shows why this needs watching (`perturbation-run.txt`). At 86% instead of 78%, the
> same pair is printed under `## Well-Established` as `_[corroborated across 2 sources]_`, because the
> rule treats values within `REL_TOL = 0.10` as agreeing. The values are still preserved, but the
> section label changes.

**3b. Source goes dark.** Run with `--simulate-timeout`. Paste the part of the briefing showing the
failed source. How is "unreachable" handled differently from "nothing to report," and why does the run
still finish?

> From `03-supply-chain/timeout-run.txt` (exit code 0):
> ```
> > Sources unavailable: logistics unavailable (timeout)
> ## Incomplete
> ### late_shipment_count  _[missing source: timeout reading logistics]_
> - missing source: timeout reading logistics
> ```
> **Unreachable vs. nothing to report:**
> - "Unreachable" is recorded as a gap with a reason: the banner at the top, plus
>   `missing source: timeout reading logistics` on the metric only logistics reports.
> - "Nothing to report" is a different annotation. `production_capacity_utilization` says
>   `missing source: no source reported this metric`.
> - A reader can therefore tell "we couldn't look" from "we looked and nobody measures this".
>
> **Why the run still finishes:** the coordinator treats each reader independently. A timeout becomes
> a `missing source` annotation instead of an exception, so the other three sources still produce
> their claims and the briefing renders.
>
> **The caveat I observed:** with logistics gone, `on_time_delivery_rate` reads
> `_[single source only]_` with just `95.0 percent — supplier_audit`, and `## Contested` says `_none_`.
> The conflict vanished with the source. The banner is the only cue, so the reader has to treat
> "single source only" as weaker evidence.

**3c. Dates as a guardrail.** Quote two claims about the same supplier with different dates. How does
requiring a date stop a time difference from reading as a contradiction?

> From `briefing.md`, `defect_rate_ppm`: `180.0 ppm — supplier_audit (as of 2026-04-10)` and
> `190.0 ppm — internal_quality (as of 2026-04-08)`. The on-time pair is also dated:
> `95.0 percent ... (as of 2026-04-10)` vs `78.0 percent ... (as of 2026-04-05)`.
>
> **How the dates help:**
> - Because every value carries its as-of date, a reader can check whether two numbers describe the
>   same period before calling them contradictory. These are all Q1 2026 figures collected within five
>   days of each other, so the 78% vs 95% gap is a real disagreement about the same quarter, not
>   "things got better later".
> - If one value had been dated a quarter earlier, the date would show it as a *trend* rather than a
>   contradiction.
> - Dates also link events to metrics. `port_disruption ... (industry_news, 2026-03-17)` describes a
>   strike "beginning March 16, 2026", which lines up with late shipments in the logistics data such as
>   SHP-26Q1-040 (promised 2026-03-12, delivered 2026-03-16).
> - Without dates, all of these would collapse into undated numbers that seem to contradict each other.

---

## 4. Synthesis

**4a. One principle.** Name the single moment in your runs (system + artifact) where *evaluate the
output, don't trust the model's word* most clearly caught something a trusting design would have
shipped.

> **System 2, `02-mortgage-extraction/live-vs-recorded.txt`.** The shipped recordings are the "golden"
> answers the test suite replays, and the suite says `25 passed`. When I compared each recording to its
> source document and to live runs:
> - The appraisal's recording has `loan.amount` `410000.0`, which is the appraised value; the document
>   states no loan amount.
> - The paystub's recording has `"base_monthly": 5673.08`, which is a bi-weekly figure.
> - Live, 5 of 6 runs on the two documents the non-nullable `loan.amount` trips over (`income_sum_mismatch`,
>   `appraisal_informal_sqft`) `CRASHED — no extraction produced`, and 2 of 3
>   paystub runs `DIFFERS from recording` (`12326.67`, `12318.5` against the true 147,500 / 12 = 12,291.67).
>
> A design that trusted "valid JSON + green tests" would have shipped all of it. Only evaluating the
> output against the source text caught it.

**4b. Confidence ≠ correctness.** Pick the system where this mattered most, and explain why using
something you observed.

> **System 1.** In my live run, the extractor's confidences were high almost everywhere. POL-2025-002
> was ≥ 0.95 on every field and POL-2025-008 ≥ 0.95. Yet the independent reviewer disagreed on 8 of
> the 9 routed policies (`reviewer_disagreement=...` in `routing_decisions.json`), and 8 of 9 went to
> `human_review`. The calibration slice shows the same thing in miniature: `conf=0.93 acc=0.00` for
> umbrella exclusions. Confidence is the model grading its own work, so it can't detect the errors it
> doesn't know it's making. An independent second read and a calibration check against labels are
> what detect them.

**4c. Apply it.** Describe a real workflow where an LLM pulls structured results from messy input.
Which pattern — validated retry with escalation, independent review with deterministic routing, or
provenance-preserving conflict annotation — would you reach for first, and what would you instrument
to know when it broke?

> **Workflow:** vendor-invoice intake for accounts payable. An LLM reads scanned PDF invoices and emits
> vendor, PO number, line items, tax and total for auto-posting.
>
> **Pattern I'd use first:** **validated retry with escalation**. Line items × quantity + tax must
> equal the total, as in System 2's validator. `format` and `consistency` failures get one retry with
> the error fed back. A missing PO number or total is `missing_source` and goes straight to an AP clerk
> with no retry, as in System 1's `premium_amount_absent`.
>
> **What I'd instrument:**
> 1. Escalation rate by category (`missing_source` vs `consistency`) per vendor. A spike means a vendor
>    changed its template.
> 2. The retry-success rate. If retries rarely fix anything, the retry budget is wasted.
> 3. The distribution of validator `delta` values, which shows when near-misses are creeping toward
>    the tolerance.
> 4. A weekly live-vs-recorded replay on a fixed golden set, like my `live-vs-recorded.txt`, so model
>    or prompt drift appears in a diff before it appears in the ledger.
> 5. A sliced calibration table by vendor × field, so one bad vendor can't hide inside a healthy
>    overall accuracy.
