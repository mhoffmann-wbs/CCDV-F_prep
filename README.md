# Gridiron Prep 🏈

An interactive study app for the **Claude Certified Developer – Foundations (CCDV-F)** exam.

It has three parts:

| | What you get |
|---|---|
| **Learn** | One lesson for each of the 25 exam skills, with links to the official docs and the Skilljar courses |
| **Check** | 485 practice questions in the style of the real exam, plus a timed 53-item mock exam with a score report |
| **Build** | Ten hands-on Python labs, themed around a fictional NFL-style league, that together make one app ("Gridiron Assistant") |

The web app runs entirely in your browser. It has no backend, never calls the Claude API and never asks for an API key. Your progress (answers, mastery and lab checklists) is stored in your browser's `localStorage`.

> The content is based on the official [Exam Guide v1.0](https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F6nizmqk8tpzpfjvt6qmmav7rh%2Fpublic%2F1783542875%2FClaude+Certified+Developer+%E2%80%93+Foundations+Exam+Guide.pdf) and the [official prep path](https://anthropic-partners.skilljar.com/path/claude-certified-developer-foundations). All questions are original; none come from the live exam.

---

## Quick start: the study app

**You need:** [Node.js](https://nodejs.org/) **22.12 or newer** (check with `node -v`) and Git.

```bash
git clone https://github.com/mhoffmann-wbs/CCDV-F_prep.git
cd CCDV-F_prep
npm install
npm run dev
```

Open the URL Vite prints (usually <http://localhost:5173>). That's it.

### Where to start

- **`/`**: the exam blueprint: 8 domains, 25 skills and their weights. Start here to see what the exam covers.
- **Learn**: read the lesson for a skill, then follow its links to the official docs.
- **Practice**: drill one skill, one domain, a weighted mixed set, or only your weak spots. Each answer is revealed with an explanation for every option.
- **Questions**: browse the whole bank, filtered by skill and by mastery.
- **Mock exam**: 53 items in 120 minutes, like the real exam. The report shows pass/fail, an *estimated* scaled score (pass mark 720) and percent correct per domain.
- **Labs**: step-by-step instructions and a checklist for each hands-on lab.

> Progress lives in the browser you use. A different browser or a private window starts fresh, and clearing site data resets it.

---

## The hands-on labs (optional)

The labs are a separate **Python** workspace in [`labs/`](labs/). Unlike the web app, they call the real Claude API, so you need your own credentials and you pay for your own usage.

**You need:**

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (`brew install uv` on macOS, or see the link)
- Claude API access: an API key from the [Claude Console](https://platform.claude.com/), or a profile created with `ant auth login`
- For L5 and L7: [Claude Code](https://claude.com/claude-code)

### Setup

```bash
cd labs
uv sync                 # creates .venv and installs dependencies
uv run pytest           # offline tests, no API key needed: should all pass
```

Then authenticate in **one** of two ways:

```bash
# Option A: a stored profile
ant auth login

# Option B: an API key in a local .env file (git-ignored, never commit it)
cp .env.example .env    # then fill in ANTHROPIC_API_KEY
```

### Running a lab

Each lab folder has a `starter.py` with numbered TODOs and a `solution.py` to compare against. Run everything from `labs/`:

```bash
uv run python L1-play-by-play/starter.py                    # your version
uv run python L1-play-by-play/solution.py                   # the reference
uv run --env-file .env python L1-play-by-play/solution.py   # if you use a .env key
```

The full instructions for each lab are in the app under **Labs**.

> 💸 **Save money while you iterate:** the labs default to `claude-opus-5-5`. Set `MODEL=claude-haiku-5-5` (in `.env` or as `MODEL=claude-haiku-5-5 uv run ...`) to use the cheapest tier.

### The ten labs

| Lab | Folder | What you build |
|---|---|---|
| L1 | `L1-play-by-play` | A streamed prose recap and a schema-checked JSON recap from a play-by-play feed |
| L2 | `L2-weekly-recaps` | All weekly recaps as one Message Batch with prompt caching, plus a cost comparison |
| L3 | `L3-injury-report` | An injury-report reader: PDF input, the Files API, citations and a photo |
| L4 | `L4-lineup-assistant` | A fantasy lineup assistant on a hand-written tool-use loop |
| L5 | `L5-league-mcp` | An MCP server over the L4 league data, used from Claude Code |
| L6 | `L6-scouting-agent` | A scouting report as a fixed workflow and as an Agent SDK supervisor with subagents |
| L7 | `L7-claude-code-repo` | A Claude Code setup: CLAUDE.md, permissions, hooks, a subagent, a skill and a plugin |
| L8 | `L8-fan-chat` | A fan chat hardened layer by layer with guardrails |
| L9 | `L9-pickem-evals` | Failure triage and an eval with a calibrated LLM judge |
| L10 | `L10-ship-it` | A release gate: model pinning, prompt versioning and an eval gate in CI |

All teams, players and games in `labs/fixtures/` are fictional.

---

## Other commands

```bash
npm run build           # type-check and build a static site into dist/
npm run preview         # serve the built site locally
npm test                # run the test suite
npm run lint            # lint with oxlint
npm run content:status  # question count per skill vs. target
```

Because the app is a static site, you can also host the `dist/` folder on a static host such as Netlify or an internal web server. It uses client-side routing and expects to be served from the root of a domain, so configure the host to serve `index.html` for unknown paths. (A sub-path like `user.github.io/repo/` would also need Vite's `base` and the router's `basename` set.)

## Troubleshooting

| Problem | Fix |
|---|---|
| `npm install` or `npm run dev` fails with an engine or syntax error | Your Node.js is too old. Install 22.12+ (e.g. `nvm install 22`) |
| Labs: `AuthenticationError` or "could not resolve authentication method" | Run `ant auth login`, or add `--env-file .env` with `ANTHROPIC_API_KEY` set |
| Labs: `uv: command not found` | Install uv (see the link above), then open a new terminal |
| My progress disappeared | Progress is per browser. Check you're in the same browser and not in a private window |

## Project layout

```
src/
  content/        lessons (MDX), questions (JSON per skill), labs (MDX), blueprint.ts
  quiz/           grading, mock-exam sampling, question view
  progress/       localStorage progress store
  pages/          app pages
labs/             Python labs workspace (uv)
  gridiron/       shared client and data loaders
  fixtures/       fictional league data
  L1-…/ … L10-…/  one folder per lab
```

To add a lesson, question or lab, add data under `src/content/`. See `CLAUDE.md` for the content rules and the checks that `npm test` enforces.
