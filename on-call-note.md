# On-call note — policy pipeline (System 1), 2 a.m. edition

**What you're looking at:** `policy-extractor pipeline` writes `routing_decisions.json` and prints a
summary: `decisions_written`, `auto_approve`, `human_review`, `spot_check`, `escalations`, and a
`pattern_summary`. A record in the summary is either a routing decision or a retry-futile escalation.

**Check first (in this order):**
1. **Did it finish?** The last capture line should read `[exit code: 0]`, and `decisions_written` +
   `escalations` should equal the number of policy files. In my run that was 9 + 1 = 10 documents in
   `data/policies/`.
2. **The escalation pattern.** `pattern_summary` groups escalations by `detected_pattern`. One
   `endorsements_absent` (POL-2025-009) is expected. A *new* pattern, or the same pattern across many
   policies, usually means a carrier changed its document layout. That's a source problem, not a model
   problem. Don't retry these; they are `missing_source` by design.
3. **The `human_review` share.** Mine was 8 of 9 (`pipeline-run.txt`). Look at `reason`:
   - `reviewer_disagreement=[...]` on the same field across many policies (here `coverage_limit` /
     `deductible`) means the extractor and reviewer interpret that field differently. Fix the field
     definition or prompt; don't loosen the router.
   - `fields_below_threshold=[...]` means the extractor itself is unsure.
   - `integration_failures` means the cross-field arithmetic broke (premium vs components).

**The signal that lies:** **confidence.** POL-2025-002 had every field ≥ 0.95 and still needed a
human (`reviewer_disagreement=['coverage_limit', 'deductible']`). The calibration slice shows
`umbrella  exclusions      n=2 conf=0.93 acc=0.00`. Never "fix" a review backlog by lowering the confidence
threshold.

**What a healthy run looks like:**
- Exit code 0, every document accounted for.
- Escalations only for documents that are genuinely missing data; each escalation took one API call,
  with no retry storm. Look for one `HTTP Request` per extract attempt in the log.
- Reviewer disagreements are scattered rather than concentrated on one field.
- `spot_check` > 0. The stratified sampler still draws from auto-approvals; POL-2025-007 was drawn
  with `"reason": "stratified drift-detection sample"`.

**Known environment gotchas:**
- On the course proxy, `claude-haiku-4-5` must be addressed as `claude-haiku-4-5-20251001`. Use
  `run_policy_extractor.py`. A 400 error saying "not available for your organization" is this, not an outage.
- The `batch` subcommand needs the Message Batches API, which the proxy does not offer.
