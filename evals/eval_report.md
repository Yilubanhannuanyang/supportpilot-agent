# SupportPilot Evaluation Report

- Generated at: `2026-10-06T00:20:46.530348`
- Overall Status: **PASS**
- Release Gate: **READY**
- Eval Suites Passed: **5/5**
- Historical Failure Records: **13**


## Release Gate

Current version satisfies all defined regression quality gates.

## Evaluation Summary

| Eval Suite | Status | Metrics |
|---|---|---|
| RAG Eval | PASS | Top1 Accuracy: 100.00%<br>Recall@3: 100.00%<br>No-answer Accuracy: 100.00% |
| Workflow Eval | PASS | Passed: 4/4<br>Accuracy: 100.00% |
| HITL Eval | PASS | Accuracy: 100.00% |
| Agent Tool Eval | PASS | Passed: 4/4<br>Accuracy: 100.00% |
| Intent Route Eval | PASS | Passed: 8/8<br>Accuracy: 100.00% |

## Quality Dimensions

- **RAG Eval**: validates retrieval ranking, Recall@3, and no-answer behavior.
- **Workflow Eval**: validates deterministic shipping workflow behavior.
- **HITL Eval**: validates approval safety rules for database write operations.
- **Agent Tool Eval**: validates whether the Agent selects the expected Tool.
- **Intent Route Eval**: validates routing between the Shipping Workflow and the normal Agent path.

## Failed Suites

No Eval Suite failed in this regression run.

## Evaluation Notes

These evaluations are small controlled regression and smoke-test suites.
A PASS result means the current implementation satisfies the defined test cases and quality gates; it should not be interpreted as production-level accuracy or safety.

Failure cases are recorded separately in:

`data/logs/eval_failures.jsonl`

Regression history is recorded in:

`data/logs/eval_regression.jsonl`