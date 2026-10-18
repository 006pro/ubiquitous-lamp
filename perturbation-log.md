# Perturbation Log

For each system, make one deliberate change to an input or configuration, predict the outcome, run
it, and record what actually happened. See the starters in the Instructions, or design your own (your
own experiment earns more credit).

All three experiments are my own design and ran on **copies** of the inputs, so the shipped fixtures
were never touched. To keep the pack small, the edited copies aren't included. Each edit is small,
and its exact before/after text is quoted below. Every quoted output line can be found with grep in
the capture file named next to it.

---

### System 1 — validated, routed pipeline

- **Change I made (file + what I changed):** I copied `data/policies/POL-2025-006.txt`, a clean umbrella
  renewal, to `perturbation/POL-2025-006-premium-blanked.txt` and blanked one
  required field, the premium. Line 13 changed from
  `Annual Premium ............................  $   612.50` to
  `Annual Premium ............................  $   [ILLEGIBLE - not stated]`.
  The rest of the document is identical. I chose the premium deliberately because it differs from the
  built-in `missing_endorsement_schedule` case (POL-2025-009), so the test is whether the futile-retry
  rule generalizes to another field.
- **Command I ran (live API):**
  `<venv>/Scripts/python run_policy_extractor.py extract perturbation/POL-2025-006-premium-blanked.txt --policy-id POL-2025-006`
  I ran the same command on the original file as the baseline.
- **What I predicted:**
  - The extractor returns a null premium rather than guessing a number.
  - The validator classifies the failure as `missing_source`, not `format` or `consistency`.
  - Retrying cannot recover information that isn't in the document, so the system should escalate
    after **one** API call with no retry.
- **What actually happened (paste the key output line):** From `01-policy-pipeline/perturbation-run.txt`:
  - Exactly one `HTTP Request: POST https://claude.vocareum.com/v1/messages` line appears, then `INFO validation_failed`.
  - `"category": "missing_source"`, `"detected_pattern": "premium_amount_absent"`, `"kind": "escalation"`
  - `"reason": "Field 'premium_amount' returned null \u2014 the source document does not contain this information. Retry is futile; escalate to human review."`
  - `[exit code: 1]`. No premium value appears anywhere in the output.

  The offline test that pins this rule passes too: `test_ac_01_02_validator_flags_null_required_as_missing_source PASSED`
  in `01-policy-pipeline/perturbation-retry-tests.txt`.
- **How this differs from the unperturbed run:** The baseline (`01-policy-pipeline/perturbation-baseline-extract.txt`)
  also used one API call, but it returned a full extraction: `"kind": "extraction"`, `"premium_amount": 612.5`,
  `"retry_count": 0`, `"validation_history": []`, and `[exit code: 0]`. The perturbed run shows
  the same call count but a different outcome. The blanked field turned the extraction into an
  escalation instead of either inventing a premium or spending 3 more retries on a field that cannot
  appear. In the full pipeline run, the unperturbed POL-2025-006 went to `human_review` only for
  `reviewer_disagreement=['deductible']` (`routing_decisions.json`). With the premium removed, it never
  reaches the router and stops at the retry boundary, the same path POL-2025-009 took
  (`"escalations": 1`, `endorsements_absent`, `missing_source` in `pipeline-run.txt`).

---

### System 2 — schema-enforced two-pass extraction

- **Change I made (file + what I changed):** I made two copies of `fixtures/documents/income_sum_mismatch.txt`
  and changed only the stated total on line 37 (`TOTAL MONTHLY EARNINGS`). The line items are
  untouched and sum to 9,642.17.
  - `perturbation/income_total_corrected.txt`: `10,892.17` became `9,642.17`, the correct sum.
  - `perturbation/income_total_off_by_25.txt`: `10,892.17` became `9,667.17`, a small but real $25 error.

  This probes both sides of the validator. Does it stay quiet when the arithmetic is right? Does it
  catch an error far smaller than the shipped $1,250 one? Its tolerance is $1 (`validator.py`:
  "The default tolerance is one dollar").
- **Command I ran (live API, new documents so no recording exists):**
  `<venv>/Scripts/mortgage-extract perturbation/<file>.txt --mode record --model claude-haiku-4-5-20251001 -v`
- **What I predicted:**
  - Corrected total: `"consistent": true` and an empty discrepancies list. The validator should not
    raise false alarms.
  - $25 error: `"consistent": false` with `delta` = -25.0, because $25 is well over the $1 tolerance.
  - Both runs should still classify as `income_verification`.
- **What actually happened (paste the key output line):** From `02-mortgage-extraction/perturbation-run.txt`:
  - Corrected total: `"stated_monthly_total": 9642.17`, then `"consistent": true,` and `[exit code: 0]`.
  - Off by $25: `"stated_monthly_total": 9667.17`, then `"consistent": false,` with
    `"calculated": 9642.17,` `"stated": 9667.17,` `"delta": -25.0`, and `[exit code: 1]`.
  - Both runs logged `classify: model=claude-haiku-4-5-20251001 ... type=income_verification`.
- **How this differs from the unperturbed run:** The unperturbed document (`02-mortgage-extraction/discrepancy-run.txt`)
  is flagged with `"calculated": 9642.17`, `"stated": 10892.17`, `"delta": -1250.0`. The difference
  is exactly the `Bonus - Performance      -            -        1,250.00` line, double-counted into the stated total.
  - Correcting the total silences the flag, so the validator reacts to arithmetic, not to the document's shape.
  - Shrinking the error from $1,250 to $25 still flags, with the delta tracking the edit exactly.
  - The clean `appraisal_informal_sqft.txt` shows the contrasting baseline: `"consistent": true`,
    `"discrepancies": []` (`extract-run.txt`).

---

### System 3 — multi-source synthesis

- **Change I made (file + what I changed):** I copied `data/meridian/` twice and edited only
  `logistics.csv`, marking some late shipments as on time. The logistics reader then derives a
  different on-time rate, while the supplier audit still claims 95%.
  - `perturbation/otd-84pct/`: 3 rows (SHP-26Q1-040..042) flipped `False` to `True`, giving 42/50 = **84%**.
  - `perturbation/otd-86pct/`: 4 rows (SHP-26Q1-040..043) flipped, giving 43/50 = **86%**.

  The conflict rule is `REL_TOL = 0.10  # values within 10% are treated as agreeing`
  (`synthesis.py`), so against 95% the boundary is 85.5%. These two edits sit on either side of it.
- **Command I ran:**
  `PYTHONUTF8=1 <venv>/Scripts/supply-chain-investigate meridian --offline --data-root perturbation/otd-84pct`
  and the same with `perturbation/otd-86pct`. As the course starter, I also ran
  `... meridian --offline --simulate-timeout`.
- **What I predicted:**
  - 84% (11.6% apart): `on_time_delivery_rate` stays in **Contested** with an escalation.
  - 86% (9.5% apart): it moves into **Well-Established** as "corroborated". A 9-point gap between
    the supplier's claim and the shipment data would read as agreement.
- **What actually happened (paste the key output line):** From `03-supply-chain/perturbation-run.txt`:
  - 84%: under `## Contested`, `### on_time_delivery_rate  _[2 sources, conflicting]_  ⚠️ ESCALATE`,
    with `95.0 percent — supplier_audit (as of 2026-04-10)` and `84.0 percent — logistics (as of 2026-04-05)`.
  - 86%: under `## Well-Established`, `### on_time_delivery_rate  _[corroborated across 2 sources]_`,
    with `95.0 percent — supplier_audit (as of 2026-04-10)` and `86.0 percent — logistics (as of 2026-04-05)`.
    `## Contested` reads `_none_`.
- **How this differs from the unperturbed run:** Unperturbed (`briefing.md`), the pair is 95% vs 78%,
  in Contested with `⚠️ ESCALATE`.
  - Moving the logistics figure 2 points (84% to 86%) flips the label from a conflict that is escalated
    to "corroborated". Both values are still printed with source and date, so provenance survives,
    but the headline section changes.
  - The `--simulate-timeout` run (`timeout-run.txt`, exit code 0) degrades in the same direction. The
    briefing correctly annotates `> Sources unavailable: logistics unavailable (timeout)` and lists
    `late_shipment_count  _[missing source: timeout reading logistics]_` under Incomplete. But
    `on_time_delivery_rate` drops to `_[single source only]_` with only the supplier's own
    `95.0 percent`, and `## Contested` reads `_none_`.
  - Both experiments show the same thing: a conflict can disappear either because the gap shrank under
    a fixed tolerance or because the dissenting source went dark. A reader has to check the coverage
    badge (`single source only`, `corroborated`) as well as the section heading.
