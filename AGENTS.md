# Agent Skills

This file configures how the engineering skills (triage, to-spec, to-tickets, wayfinder, domain-modeling, etc.) interact with this repo. See the files under `docs/agents/` for details.

## Agent skills

### Issue tracker

Issues and specs are tracked as GitHub issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) map 1:1 to GitHub labels with the same names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
