# Packaging the setup as a plugin

`gridiron-tools/` bundles the three reusable parts of this repo's Claude Code setup:

```text
plugin/                              <- marketplace root
├── .claude-plugin/marketplace.json  <- catalog: name, owner, plugins[]
└── gridiron-tools/                  <- the plugin
    ├── .claude-plugin/plugin.json   <- manifest (only "name" is required)
    ├── skills/game-preview/SKILL.md <- runs as /gridiron-tools:game-preview
    ├── agents/test-runner.md        <- subagent gridiron-tools:test-runner
    ├── hooks/hooks.json             <- PreToolUse hook, paths via ${CLAUDE_PLUGIN_ROOT}
    └── scripts/protect_data.py      <- same script as .claude/hooks/protect_data.py
```

Only `plugin.json` goes inside `.claude-plugin/`. Skills, agents and hooks sit at the plugin root.
The copies here must match the files under `../.claude/`; `tests/test_l7_hook.py` checks that.

## Try it without a marketplace

```bash
claude plugin validate ./plugin/gridiron-tools
claude --plugin-dir ./plugin/gridiron-tools      # loads it for this session only
```

## Install it from the marketplace

```bash
claude plugin validate ./plugin                  # checks marketplace.json and each plugin
claude plugin marketplace add ./plugin
claude plugin install gridiron-tools@gridiron-marketplace                  # user scope (default)
claude plugin install gridiron-tools@gridiron-marketplace --scope project  # whole team, via .claude/settings.json
claude plugin install gridiron-tools@gridiron-marketplace --scope local    # just you, just this repo
```

- `marketplace.json` needs `name`, `owner` and `plugins`; each entry needs `name` and `source`. Write a relative `source` from the marketplace root (the folder that holds `.claude-plugin/`), and never use `..`.
- Keep the entry `name` and the `plugin.json` `name` the same. The entry name is the install id, and the manifest name prefixes the skills.
- **User scope**: you, every project on this machine. **Project scope**: everyone in the repo, through the committed `.claude/settings.json` (each teammate still installs it once). **Local scope**: you, this repo only.
- A plugin runs code as you (the hook is a Python script), and each skill and agent description sits in context every turn. Review a plugin before you install it.
- Some subagent fields are ignored in plugin agents: `hooks`, `mcpServers` and `permissionMode`. Put hooks in `hooks/hooks.json` instead.
