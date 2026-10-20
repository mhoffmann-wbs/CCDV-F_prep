#!/usr/bin/env bash
# Headless Claude Code review for CI. Run it from the project root:
#   ANTHROPIC_API_KEY=... ci/claude-review.sh
#
# Why every flag is explicit:
# - `claude -p` starts in `default` (Manual) mode, not the interactive auto
#   mode, and nobody is there to answer a prompt. Anything that needs approval
#   is denied unless an allow rule covers it. So we name the mode and the tools.
# - `--bare` skips auto-discovery (CLAUDE.md, hooks, skills, plugins, MCP
#   servers, ~/.claude). Without it, a -p run in an untrusted checkout would load
#   whatever the branch's .claude/ and .mcp.json contain, with no trust dialog.
#   We pass back only what we chose: the settings file and CLAUDE.md. In a real
#   pipeline, read them from the base branch (git show origin/main:CLAUDE.md)
#   so a pull request can't loosen its own rules. Bare mode needs
#   ANTHROPIC_API_KEY; it never reads a subscription login.
# - `dontAsk` denies anything not pre-approved. The review only reads and runs
#   tests, so Edit and Write are also removed outright.
# - `--max-turns` and `--max-budget-usd` cap a runaway loop.
set -euo pipefail

: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY (a CI secret, never a committed file)}"

result_json=$(claude --bare -p \
  "Review the changes on this branch for bugs. Run the test suite with 'uv run pytest'. \
Reply with PASS or FAIL on the first line, then at most 10 bullet points citing file:line." \
  --settings .claude/settings.json \
  --append-system-prompt-file CLAUDE.md \
  --permission-mode dontAsk \
  --allowedTools "Read,Grep,Glob,Bash(uv run pytest *),Bash(git diff *),Bash(git log *)" \
  --disallowedTools "Edit,Write,NotebookEdit,WebFetch,WebSearch" \
  --max-turns 15 \
  --max-budget-usd 1.00 \
  --output-format json)

# --output-format json returns one object: `result` holds the reply text,
# plus `is_error`, `session_id` and `total_cost_usd` (an estimate).
echo "$result_json" | jq -r '.result'
echo "cost (estimate): \$$(echo "$result_json" | jq -r '.total_cost_usd')"

if [[ "$(echo "$result_json" | jq -r '.is_error')" == "true" ]]; then
  echo "Claude run failed" >&2
  exit 1
fi
if ! echo "$result_json" | jq -r '.result' | head -n 1 | grep -q '^PASS'; then
  exit 1
fi
