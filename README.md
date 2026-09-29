# Maya Command Library

Lightweight Maya commands and tools managed through Jira project **MCL**.

## Project links

- Jira: https://coldrain1994.atlassian.net
- Project key: `MCL`
- Workflow: `MCL-WORKFLOW-V1`

## Tool catalog

| Tool | Jira | Purpose | Current attempt |
| --- | --- | --- | --- |
| [MCL Model Renamer](./tools/mcl-model-renamer/) | MCL-1 | Sequential naming plus two-model Face Count High/Low naming | 0.2.0 / V2 |

## Structure

Each maintained tool lives in its own directory under `tools/` and keeps its own source, README, changelog, launcher, and focused tests where practical.

## Delivery rule

A feature is not considered accepted because code exists or tests pass. Fixed-version source/download, complete Maya launch code, usage instructions, verification scope, and explicit user acceptance are recorded in the corresponding MCL Jira item.
