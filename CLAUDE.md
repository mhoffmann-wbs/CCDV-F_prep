# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**`PLAN.md` is the build plan and sets the order of work.** It covers the skill-by-skill content map, the question-bank targets, the lab specs and the phases (§5 records what is done). Phases 0 and 1 are complete: the scaffold, the blueprint, the question schema, the content tests and the 3 official sample items. Everything marked *planned* below doesn't exist yet. As parts get built, update this file so it describes what actually exists.

## Purpose

This is an interactive study app for the **Claude Certified Developer – Foundations (CCDV-F)** exam. It has three pillars:
- **Learn**: one lesson for each of the 25 blueprint skills, linking to official docs and Skilljar courses.
- **Check**: practice and mock exams written in the style of the real exam.
- **Build**: ten NFL-themed hands-on labs that together form one capstone app called "Gridiron Assistant".

## Authoritative sources

- **Exam Guide v1.0** (July 2026) is the single source of truth for domains, skill weights and exam format. [PDF](https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F6nizmqk8tpzpfjvt6qmmav7rh%2Fpublic%2F1783542875%2FClaude+Certified+Developer+%E2%80%93+Foundations+Exam+Guide.pdf)
- **Official prep path** (5 Skilljar courses, login required, so link to them and don't summarize them). [Path](https://anthropic-partners.skilljar.com/path/claude-certified-developer-foundations)

Use these, not third-party prep sites. If the guide gets a new version, update `src/content/blueprint.ts` first. The content tests then show which lessons and question pools need to change.

## Exam format the app must mirror

- 53 items in 120 minutes.
- Items are multiple-choice or multiple-response, and **each item states how many answers to select**.
- Pass mark is a scaled 720 on a 100–1,000 scale.
- The score report shows pass/fail, the scaled score, and percent correct per domain.
- Items are scenario-based ("which approach best fits…"), with one defensible answer and plausible distractors. Guide §8 has the 3 official samples.

## Architecture

- **Stack**: Vite 8 + React 19 + TypeScript 6, Tailwind v4 (theme colours `field`, `field-dark`, `chalk`, `pigskin` are defined in `src/index.css` via `@theme`), React Router 8 (imported from `react-router`), Zod 4, MDX (`@mdx-js/rollup`, wired up but not used yet), Vitest 5 + RTL, and oxlint for linting. It is a static SPA with no backend. *Planned:* progress stored in `localStorage` behind one versioned storage module.
- **Content is data.** Everything lives under `src/content/`, and the UI renders it generically. To add a lesson, question or lab, add data. Don't add new components for it.
  - `blueprint.ts`: 8 domains and 25 skills (ids like `"2.3"`), exact weights, Skilljar course mapping, lab mapping and exam-format constants. It also holds `questionTarget()` (pool size per skill) and `allocateItems()` (largest-remainder split of the 53 mock items). Mock-exam sampling, readiness scoring and the content tests all derive from this file.
  - `schema.ts`: the Zod `QuestionSchema`, with cross-field checks: `correct.length === selectCount`, correct ids must exist among the options, and `skillId` must be in the blueprint.
  - `questions/domain-<n>.json`: one array per domain. They are loaded and validated through `import.meta.glob` in `questions/index.ts`. Ids are `q-<skillId>-NNN`, or `official-N` for the Exam Guide samples, which also carry `official: true`.
  - *Planned:* `lessons/<skillId>.mdx`, `labs/L<n>.mdx`.
- **`content.test.ts`** checks blueprint integrity (weights sum to 100, domain weights match the guide, allocation) and question-bank integrity (schema, file/domain match, unique ids). The question *targets* are not enforced by tests. Track them with `npm run content:status`.
- *Planned:* the **mock exam** draws its items per skill using `allocateItems()`. The scaled score is an estimate and must be labelled as one.
- *Planned:* **`labs/`** is a separate TS workspace that learners run themselves with their own `ANTHROPIC_API_KEY`, using bundled fictional NFL JSON fixtures. The web app never calls the Claude API and never stores keys.

## Content rules

- Before writing API, model, pricing, Agent SDK or MCP details into lessons, questions or labs, check them with the `claude-api` skill. Never write them from memory. Skill 5.3 explicitly tests breaking changes across model releases.
- Write every question yourself. Never reproduce live exam content: candidates are under an NDA.
- Explanations should follow the reasoning style of the guide's sample rationales: say why the right answer fits the stated constraint, and why each distractor misses it.

## Commands

```bash
npm run dev             # Vite dev server
npm run build           # tsc -b + production build
npm run lint            # oxlint
npm test                # Vitest (run once); npm run test:watch for watch mode
npm run content:status  # question count per skill vs. target (Node runs the TS directly)
npx vitest run src/content/content.test.ts   # single file
npx vitest run -t "blueprint"                # single test by name
```
