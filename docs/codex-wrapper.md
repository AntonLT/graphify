# Codex Wrapper Notes

This branch preserves AntonLT's Codex/Graphify setup from the installed
`graphifyy==0.8.49` baseline.

## Baseline

- Upstream: `https://github.com/Graphify-Labs/graphify`
- Fork: `https://github.com/AntonLT/graphify`
- Branch: `anton/codex-graphify-wrapper`
- Baseline tag: `v0.8.49`
- Installed command: `/Users/anton/.local/bin/graphify`
- Installed package env:
  `/Users/anton/.local/share/uv/tools/graphifyy`

## Codex Integration

Codex-facing behavior is currently carried by the local skill:

- `/Users/anton/.codex/skills/graphify/SKILL.md`
- `/Users/anton/.codex/skills/graphify/references/`

Project-level agent rules also expect Graphify to be used before broad source
browsing when `graphify-out/graph.json` exists.

## Local Efficiency Rules

- Preserve `graphify-out/cache` and `graphify-out/manifest.json` during active
  work; deleting them can force full semantic re-extraction.
- Prefer `graphify query`, `graphify path`, and `graphify explain` for
  architecture/navigation questions before broad source reads.
- Use exact `rg` and scoped file reads after Graphify for symbols, call sites,
  tests, and edits.
- Keep command output quiet; avoid raw session JSONL or large dumps.

## Install From Fork

Use this when the fork branch should replace the PyPI-installed tool:

```bash
uv tool install --reinstall --from git+https://github.com/AntonLT/graphify.git@anton/codex-graphify-wrapper graphifyy
```

Keep package changes small and mergeable. Prefer documenting Codex wrapper
behavior here or in the Codex skill unless runtime package behavior must change.
