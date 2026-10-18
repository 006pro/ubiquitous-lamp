# Evidence Pack — Evaluation and Observability Capstone

**Author:** Radhakrishnan · **Run date:** 2026-10-18 · **Environment:** see [`environment.txt`](environment.txt)

This pack covers the three reference systems from the course repo. Each one went through four steps:
reproduce, run, perturb and reflect. The layout follows the provided starter `README.md`. Every value
quoted in [`reflection-brief.md`](reflection-brief.md) and [`perturbation-log.md`](perturbation-log.md)
can be found in the file named next to it.

| Folder | System (final-exercise `solution/` in the course repo) | Tests | mypy / ruff |
|---|---|---|---|
| [`01-policy-pipeline/`](01-policy-pipeline/) | Validated, Routed Insurance Policy Extraction Pipeline / `04-hitl-routing` | 45 passed (3 live skipped) | clean / clean |
| [`02-mortgage-extraction/`](02-mortgage-extraction/) | Resilient Mortgage Document Extraction System / `04-validate-mathematical-consistency` | 25 passed | clean / clean |
| [`03-supply-chain/`](03-supply-chain/) | Supply Chain Risk with Multi-Source Synthesis / `03-resilient-coordinator` | 34 passed | clean / clean |

## Checklist → file

| Checklist item | File(s) |
|---|---|
| `environment.txt`: Python version and OS | `environment.txt` |
| Each system: full `pytest` output + `mypy`/`ruff` output | `0N-*/tests.txt`, `0N-*/static-checks.txt` |
| System 1: `routing_decisions.json` + calibration output | `01-policy-pipeline/routing_decisions.json`, `pipeline-run.txt`, `calibration-report.txt` |
| System 2: the three `mortgage-extract` runs | `02-mortgage-extraction/extract-run.txt` (appraisal_informal_sqft, income_missing_bonus), `discrepancy-run.txt` (income_sum_mismatch) |
| System 3: the briefing + the `--simulate-timeout` run | `03-supply-chain/briefing.md`, `investigation-run.txt`, `timeout-run.txt` |
| `perturbation-log.md`: one experiment per system | `perturbation-log.md` (captures in `0N-*/perturbation-run.txt`) |
| `reflection-brief.md`: every answer grounded in a named artifact | `reflection-brief.md` |
| At least one screenshot per system | `0N-*/screenshots/*.png` |

## Contents

```
capstone-submission/
├── README.md                    # this index
├── environment.txt              # OS, Python, venv setup, Windows/proxy notes
├── reflection-brief.md          # the completed brief
├── perturbation-log.md          # one own-design experiment per system
├── on-call-note.md              # stand-out: 2 a.m. runbook for System 1
│
├── 01-policy-pipeline/
│   ├── tests.txt                      # pytest tests/ -v
│   ├── static-checks.txt              # mypy + ruff
│   ├── pipeline-run.txt               # LIVE: pipeline data/policies/ --routing-out routing_decisions.json --seed 42
│   ├── routing_decisions.json         # generated routing output (9 decisions)
│   ├── calibration_report.py          # the provided calibration snippet
│   ├── calibration-report.txt         # its output
│   ├── run_policy_extractor.py        # launcher: pins claude-haiku-4-5 -> -20251001 for the course proxy
│   ├── perturbation-baseline-extract.txt  # LIVE: unperturbed extract
│   ├── perturbation-run.txt           # LIVE: premium-blanked extract (missing_source escalation)
│   ├── perturbation-retry-tests.txt   # pytest tests/test_us01_retry.py -v
│   └── screenshots/02-pipeline-run.png
│
├── 02-mortgage-extraction/
│   ├── tests.txt
│   ├── static-checks.txt
│   ├── extract-run.txt                # appraisal_informal_sqft + income_missing_bonus (--mode replay -v)
│   ├── discrepancy-run.txt            # income_sum_mismatch (validator reports delta -1250.0)
│   ├── perturbation-run.txt           # LIVE: stated total corrected / off by $25
│   ├── live-vs-recorded.txt           # stand-out: 3 live runs per fixture vs the shipped recordings
│   └── screenshots/01-discrepancy-run.png
│
└── 03-supply-chain/
    ├── tests.txt                      # pytest tests/ -q
    ├── static-checks.txt
    ├── investigation-run.txt          # supply-chain-investigate meridian --offline
    ├── briefing.md                    # generated briefing (Well-Established / Contested / Incomplete)
    ├── timeout-run.txt                # --simulate-timeout (completes, logistics annotated)
    ├── perturbation-run.txt           # on-time rate at 84% vs 86% (tolerance boundary)
    └── screenshots/02-timeout-run.png
```

The systems' source code is in the course repo and isn't duplicated here. Run each one from that
project's final `solution/` folder, as listed in the table above.

**About the screenshots.** Each PNG is rendered from the captured terminal output named in its header
line ("rendered from captured output: …"), so it shows exactly what is in the `.txt`.

**Stand-out items attempted:**
- **Regenerate live fixtures:** `02-mortgage-extraction/live-vs-recorded.txt`.
- **Write the on-call note:** `on-call-note.md`.
- **Own-design perturbations:** all three, including a threshold-boundary experiment for System 3.
