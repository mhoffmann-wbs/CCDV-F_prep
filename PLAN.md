# Build Plan — CCDV-F Prep App ("Gridiron Prep")

This plan is based on two official sources:
- **Exam Guide v1.0** (effective July 2026, exam code CCDV-F). It is the authoritative blueprint. [PDF](https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F6nizmqk8tpzpfjvt6qmmav7rh%2Fpublic%2F1783542875%2FClaude+Certified+Developer+%E2%80%93+Foundations+Exam+Guide.pdf)
- **Official prep path** on Anthropic Partner Academy (Skilljar): 5 courses, about 13 hours. [Path](https://anthropic-partners.skilljar.com/path/claude-certified-developer-foundations)

Where this plan and the Exam Guide disagree, the Exam Guide wins.

---

## 1. Exam facts the app must mirror (Exam Guide §5, §9)

| Fact | Value | App consequence |
|---|---|---|
| Items | 53 | The mock exam has exactly 53 items |
| Format | Multiple-choice and multiple-response; **each item states how many to select** | Item schema needs `selectCount`; the stem shows "(Select TWO)" |
| Time | 120 min | Mock exam has a 120-minute countdown, flag-for-review, and a review screen |
| Pass | Scaled 720 on a 100–1,000 scale | Show an estimated scaled score (linear mapping, clearly labelled as an estimate) |
| Report | Pass/fail, scaled score, and **percent correct by domain** | The results screen copies this layout |
| Style | Scenario-based "which approach best fits…" (see §8 samples) | Every item is a scenario with one best answer and plausible distractors |

## 2. Blueprint → content map (25 skills)

Each skill is one lesson page plus one question pool. Question pool sizes are about 3 × the skill's weight in percent, with a minimum of 6, which gives **~303 items**. That is enough for about 5 mock exams that don't overlap much. The mock exam allocates its 53 items across skills by weight using largest-remainder rounding.

The **Skilljar** column maps each skill to the official course that covers it: C1 MSO Foundations · C2 Production-Grade Prompting, Agents & Tool Use · C3 Claude Code, MCP & Integration · C4 Production Engineering, Evals & Security · C5 Accelerators & IP Contribution.

| # | Domain / Skill | Weight | Items | Skilljar | NFL lab |
|---|---|---|---|---|---|
| **1** | **Agents and Workflows** | **14.7** | | | |
| 1.1 | Agent Architecture (workflow vs agent, supervisor hierarchies, subagents) | 4.5 | 14 | C2 | L6 |
| 1.2 | Agent Construction (Agent SDK, custom loops/harnesses, self-hosted vs Anthropic-hosted, hooks) | 5.3 | 16 | C2 | L6 |
| 1.3 | Agent Patterns & Frameworks (tool loops, sub-agents, memory, context mgmt; Strands, LangGraph, PydanticAI) | 4.9 | 15 | C2 | L4, L6 |
| **2** | **Applications and Integration** | **33.1** | | | |
| 2.1 | Understanding Requirements | 3.4 | 10 | C3, C5 | L10 |
| 2.2 | Systems Life Cycle | 2.8 | 8 | C5 | L10 |
| 2.3 | Claude API Mechanics (messages, tools, streaming, vision, thinking, caching, 3rd-party vendors, batch vs realtime) | 6.8 | 20 | C1, C2 | L1, L2, L3 |
| 2.4 | Software Engineering Foundations (REST, JSON, async, VCS, SDLC, code review, refactoring) | 7.4 | 22 | C1, C3 | all |
| 2.5 | Claude Application Design (instruction interpretation across interfaces, content boundaries, schema design, session hygiene, plugins) | 8.6 | 26 | C2, C3 | L1, L7 |
| 2.6 | Configuration Management (CLAUDE.md, settings.json, model pinning, prompt versioning, plugin deps) | 4.1 | 12 | C3, C5 | L7, L10 |
| **3** | **Claude Code** | **3.1** | | | |
| 3.1 | Claude Code Operation (rules, skills, commands, agents, memory, headless/streaming/auto mode, CLAUDE.md hierarchy, settings.json) | 3.1 | 9 | C3 | L7 |
| **4** | **Eval, Testing, and Debugging** | **2.6** | | | |
| 4.1 | Debugging & Error Handling (error types, recovery, trace analysis, integration-vs-model isolation) | 2.6 | 8 | C4 | L9 |
| **5** | **Model Selection and Optimization** | **16.8** | | | |
| 5.1 | LLM Fundamentals (tokens, context window, sampling, non-determinism, fast mode, extended/adaptive thinking, effort, zero/one/multi-shot) | 5.2 | 16 | C1 | L1 |
| 5.2 | Technical Fundamentals (SDKs wrapping REST, websockets) | 6.1 | 18 | C1 | L1, L5 |
| 5.3 | Model Selection & Tradeoffs (Opus/Sonnet/Haiku, quality/latency/cost, breaking changes across releases) | 2.7 | 8 | C1, C5 | L2 |
| 5.4 | Cost & Token Management (usage tracking, cost modelling, prompt caching, cache checkpointing) | 2.8 | 8 | C4 | L2 |
| **6** | **Prompt and Context Engineering** | **11.0** | | | |
| 6.1 | Context Engineering (drift/bloat, tool-output pruning, compaction, subagent isolation) | 3.8 | 11 | C2 | L4, L6 |
| 6.2 | Prompt Engineering (clarity, few-shot, system vs user, output constraints, iteration, input sanitization) | 4.6 | 14 | C2 | L1 |
| 6.3 | Output Handling (structured output, validation, defensive parsing, skepticism) | 2.6 | 8 | C2 | L1, L9 |
| **7** | **Security and Safety** | **8.1** | | | |
| 7.1 | AI Application Security (prompt injection, jailbreaks, untrusted input, leakage, PII, authN/authZ) | 3.2 | 10 | C4 | L8 |
| 7.2 | Guardrails & Safe Deployment (layered guardrails, least privilege, IAM) | 2.3 | 7 | C4 | L8 |
| 7.3 | Claude Hooks (blocking destructive actions) | 1.0 | 6 | C3 | L6, L7 |
| 7.4 | Identity, Secrets & Key Management | 1.6 | 6 | C3, C4 | L8, L10 |
| **8** | **Tools and MCPs** | **10.6** | | | |
| 8.1 | Tool Implementation (schemas, descriptions, errors, client vs server tools, approval patterns, dispatch) | 4.4 | 13 | C2 | L4 |
| 8.2 | MCP Server Development (tools/resources/prompts, stdio vs remote transports, deployment) | 2.1 | 6 | C3 | L5 |
| 8.3 | Agentic Customization (built-in tools vs custom tools vs Skills vs MCP) | 4.1 | 12 | C3 | L5, L7 |

The six heaviest skills (**2.5, 2.4, 2.3, 5.2, 1.2, 5.1**) carry 39.4% of the exam. Content depth should follow that.

## 3. NFL hands-on labs ("Gridiron Assistant")

There is **one cumulative capstone** with ten labs. Exam Guide §7 recommends building "at least one Claude application that exercises the API, integrates one or more tools, applies basic prompt and context engineering, and includes simple security and evaluation practices", and these labs together do exactly that. Each lab has the same parts: a goal, a starter folder, a step checklist, a "done when" check, "exam angle" notes (the traps it teaches), and links to docs and Skilljar.

The learner runs everything locally with their own `ANTHROPIC_API_KEY`. Data comes from small bundled JSON fixtures (fictional players and games), so there is no dependency on a live NFL API.

| Lab | Build | Skills |
|---|---|---|
| L1 | **Play-by-play summarizer**: system prompt, XML-tagged input, few-shot, streaming, JSON output validated with Zod, token counting | 2.3, 2.5, 5.1, 5.2, 6.2, 6.3 |
| L2 | **Weekly recap batch job**: Message Batches API for all games, a cached shared league context (prompt caching), a cost report comparing Haiku, Sonnet and Opus | 2.3, 5.3, 5.4 |
| L3 | **Injury report reader**: send the PDF or image of a team injury report, reuse it through the Files API | 2.3 |
| L4 | **Fantasy lineup assistant**: custom tools (`get_player_stats`, `get_injury_status`, `set_lineup` with approval), a manual tool-use loop, parallel tool calls, tool-output pruning | 1.3, 6.1, 8.1 |
| L5 | **League Stats MCP server**: expose L4's tools plus resources and prompts over stdio, then remote; connect it to Claude Code and to the API app | 5.2, 8.2, 8.3 |
| L6 | **Scouting report agent**: Agent SDK, a supervisor with "film" and "stats" subagents, memory across sessions, a hook that blocks writes outside `reports/`, and a comparison against a fixed workflow version | 1.1, 1.2, 1.3, 6.1, 7.3 |
| L7 | **Claude Code on the repo**: `/init`, the CLAUDE.md hierarchy, rules, `settings.json` permissions, a custom slash command `/game-preview`, a Skill, a PreToolUse hook, packaging as a plugin, a headless run in CI | 2.5, 2.6, 3.1, 7.3, 8.3 |
| L8 | **Fan chat guardrails**: injection-laden fan messages, untrusted-content isolation, PII redaction, layered guardrails, secrets stored in env or a vault and never in the prompt | 7.1, 7.2, 7.4 |
| L9 | **Pick'em evals and debugging**: an eval set of graded predictions, code graders plus LLM-as-judge calibrated against hand labels, error classification (retry 429/529 vs fail fast on 400), trace review | 4.1, 6.3 |
| L10 | **Ship it**: model version pinning, prompt versioning, a decision record comparing first-party API, Bedrock and Vertex, a requirements and SDLC checklist | 2.1, 2.2, 2.6, 7.4 |

## 4. App features

1. **Dashboard**: readiness per domain, weighted by the blueprint, plus the weakest 5 skills and a "next step" suggestion.
2. **Study path**: the 25 skill lessons, grouped by domain. Each lesson has:
   - TL;DR
   - key concepts
   - "Exam traps" (based on the reasoning shown in the §8 sample rationales)
   - an NFL mini-example
   - official links (docs, plus the matching Skilljar course)
   - a "Mark as read" button
3. **Practice**: choose a domain or skill and get immediate feedback, with an explanation for every option.
4. **Mock exam**: 53 items, 120 minutes, flag and review, results in the official report format.
5. **Weak-area drill**: picks items from the skills with the lowest accuracy that haven't been seen recently.
6. **Labs**: lab pages with checklists that are saved to progress.
7. **Resources**: the Skilljar path, the 9 recommended prerequisite courses, and Anthropic docs. It also links registration (Partner Academy, then Pearson VUE) and summarizes the policies: retake waits of 14, 30 and 90 days, and 12-month validity.

## 5. Build order (what to create now)

**Status (2026-10-20):**
- Phase 0 is done for the web app. `labs/` is not set up yet; it is deferred to Phase 5.
- Phase 1 is done. Lesson and lab schemas will be added along with their phases.
- The 3 official sample items are seeded.
- Phase 2 is done: the progress store, practice mode, the mock exam (weighted sampler, timer, flag/review, results report) and 12 original 2.3 items.
- Phase 3 is done: all 25 lessons (`src/content/lessons/*.mdx`), checked against the docs on 2026-10-20.
- Phase 4 is done: 303 items (60 multi-response; difficulty about 29/51/20%; keys balanced A–D; all 135 links verified with `content:links`).
- Phase 5 is done (2026-10-26): all ten labs, in **Python** (uv), built in order of the exam weight they cover. Their offline tests run without a key; the live steps have not yet been run end to end against the API.
- Phase 6 is done: Scoreboard dashboard, weak-area drill, dark mode and phone layout.

### Phase 0: Scaffold
- `git init`. Vite + React + TS, Tailwind, React Router, Zod, Vitest + RTL, ESLint, MDX via `@mdx-js/rollup`
- Starting with `labs/`: a separate TS workspace with `@anthropic-ai/sdk`, `@anthropic-ai/claude-agent-sdk` and `@modelcontextprotocol/sdk`

### Phase 1: Content model (foundation; everything else depends on it)
- `src/content/blueprint.ts`: 8 domains and 25 skills with the exact weights from §2, Skilljar course mapping, and lab mapping
- Zod schemas for `Question`, `Lesson` frontmatter and `Lab`
- `content.test.ts` checks that:
  - weights sum to 100
  - every skill has ≥ its target number of items and a lesson
  - every option has an explanation
  - `correct.length === selectCount`
  - there are no duplicate ids

### Phase 2: Engine + vertical slice
- Progress store in localStorage, versioned so it can be migrated later
- Question renderer that handles single and multi-select
- Practice mode, mock exam (weighted sampler, timer, flag/review), results report
- Seed questions: the **3 official sample items** (labelled "Official sample") plus about 10 original items for skill 2.3, to exercise the whole flow end to end

### Phase 3: Lessons (heaviest skills first)
- Order: 2.5 → 2.4 → 2.3 → 5.2 → 1.2 → 5.1 → 1.3 → 6.2 → 1.1 → 8.1, then the rest

### Phase 4: Question bank
- About 303 items in the same order as the lessons
- About 20% multiple-response
- Every item cites its doc in `sourceLinks`

### Phase 5: Labs
- Write L1 and L4 first: they cover the most weight and are prerequisites for L5 and L6
- Then L2, L6, L7, L5, L8, L9, L3, L10

### Phase 6: Polish
- Dashboard readiness, weak-area drill, dark mode, mobile layout

## 6. Content rules
- Write every item yourself. Never reproduce live exam content: candidates sign an NDA (§13), and the app must not encourage using dumps.
- Check model IDs, API parameters, pricing and feature names against current docs (in Claude Code, use the `claude-api` skill) before writing them. The exam tests breaking changes across model releases (5.3), so content has to be current.
- Skilljar lessons require a login, so link to the courses rather than summarizing their contents.

## 7. Notes for question writers (from lesson research, 2026-10-20)

Facts in current docs that differ from older material. Use them for correct answers and plausible distractors, and re-check them before relying on them.
- **Models and API**
  - Non-default `temperature`, `top_p` and `top_k` return a 400 on current models, so "set temperature to 0" is a good distractor.
  - `budget_tokens` thinking and assistant prefill are rejected.
  - Opus 5.5 can't turn thinking off; its default effort is `medium`.
  - Forced `tool_choice` (`any` or `tool`) is rejected on Opus 5.5, Sonnet 5.5 and Fable 5.1.
- **Model IDs:** dateless IDs (`claude-sonnet-5-5`) are fixed snapshots, not "latest" pointers.
- **Errors**
  - A usage tier's monthly spend cap returns a 429 with no `retry-after` that keeps failing. A spend limit the org sets itself returns a 400.
  - Errors can arrive mid-stream after an HTTP 200.
- **Structured outputs:** don't combine them with citations (a 400). Validate enum values anyway.
- **Claude Code**
  - Interactive sessions start in auto mode (v2.1.283+), while `claude -p` and the Agent SDK start in `default` (Manual).
  - Deny rules and hook `deny` apply even in `bypassPermissions`.
  - Custom commands have merged into skills.
  - Claude Code reads `AGENTS.md` when there's no `CLAUDE.md`.
- **Agent SDK**
  - The default system prompt is minimal; the `claude_code` preset is opt-in.
  - CLAUDE.md is loaded through `settingSources` and injected into the conversation, not the system prompt.
- **MCP:** the 2026-07-28 spec is stateless. There's no `initialize` handshake; a mandatory `server/discover` replaces it. Sampling and logging are deprecated. The exam guide may predate this, so avoid stems that depend on handshake details.
- **API keys:** they can have an expiration. Personal and service-account keys are preferred; workspace keys are legacy.
