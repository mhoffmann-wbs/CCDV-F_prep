// Single source of truth for the CCDV-F exam blueprint.
// Source: Claude Certified Developer – Foundations Exam Guide v1.0 (effective July 2026), §5 and §6.
// If the guide is revised, update this file first; content tests will flag what else must change.

export const EXAM_GUIDE = {
  version: '1.0',
  effective: '2026-07',
  code: 'CCDV-F',
  url: 'https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F6nizmqk8tpzpfjvt6qmmav7rh%2Fpublic%2F1783542875%2FClaude+Certified+Developer+%E2%80%93+Foundations+Exam+Guide.pdf',
} as const

export const EXAM_FORMAT = {
  items: 53,
  minutes: 120,
  scaledMin: 100,
  scaledMax: 1000,
  passingScaled: 720,
  feeUsd: 125,
  validityMonths: 12,
  retakeWaitDays: [14, 30, 90],
  maxAttemptsPer12Months: 4,
} as const

export type CourseId = 'C1' | 'C2' | 'C3' | 'C4' | 'C5'
export type LabId = 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6' | 'L7' | 'L8' | 'L9' | 'L10'

/** Official prep path on the Anthropic Partner Academy (Skilljar). Login required. */
export const SKILLJAR_PATH_URL =
  'https://anthropic-partners.skilljar.com/path/claude-certified-developer-foundations'

export const COURSES: Record<CourseId, { title: string; minutes: number; url: string }> = {
  C1: { title: 'MSO Foundations', minutes: 57, url: `${SKILLJAR_PATH_URL}/mso-foundations` },
  C2: {
    title: 'Production-Grade Prompting, Agents & Tool Use',
    minutes: 209,
    url: `${SKILLJAR_PATH_URL}/production-grade-prompting-agents-tool-use`,
  },
  C3: {
    title: 'Claude Code, MCP & Integration',
    minutes: 142,
    url: `${SKILLJAR_PATH_URL}/claude-code-mcp-integration`,
  },
  C4: {
    title: 'Production Engineering, Evals & Security',
    minutes: 211,
    url: `${SKILLJAR_PATH_URL}/production-engineering-evals-security`,
  },
  C5: {
    title: 'Accelerators & IP Contribution',
    minutes: 155,
    url: `${SKILLJAR_PATH_URL}/accelerators-ip-contribution`,
  },
}

export const LABS: Record<LabId, string> = {
  L1: 'Play-by-play summarizer',
  L2: 'Weekly recap batch job',
  L3: 'Injury report reader',
  L4: 'Fantasy lineup assistant',
  L5: 'League Stats MCP server',
  L6: 'Scouting report agent',
  L7: 'Claude Code on the repo',
  L8: 'Fan chat guardrails',
  L9: "Pick'em evals & debugging",
  L10: 'Ship it',
}

export interface Skill {
  /** e.g. "2.3" — domain number, then skill number within the domain. */
  id: string
  title: string
  /** Share of the whole exam, in percent (Exam Guide §6). */
  weight: number
  /** Skill description, summarized from the Exam Guide. */
  summary: string
  courses: CourseId[]
  labs: LabId[]
}

export interface Domain {
  id: number
  title: string
  skills: Skill[]
}

export const DOMAINS: Domain[] = [
  {
    id: 1,
    title: 'Agents and Workflows',
    skills: [
      {
        id: '1.1',
        title: 'Agent Architecture',
        weight: 4.5,
        summary:
          'Principles, patterns and tradeoffs of agent vs. workflow architecture: decision criteria for workflow vs. agent, manager/supervisor hierarchies, and the role of subagents.',
        courses: ['C2'],
        labs: ['L6'],
      },
      {
        id: '1.2',
        title: 'Agent Construction with Claude',
        weight: 5.3,
        summary:
          'Claude Agent SDK, custom agent loops and harnesses, managed deployment models (self-hosted vs. Anthropic-hosted), and hooks for deterministic actions.',
        courses: ['C2'],
        labs: ['L6'],
      },
      {
        id: '1.3',
        title: 'Agent Patterns and Frameworks',
        weight: 4.9,
        summary:
          'Tool-use loops, sub-agents, memory, context-window management, and agentic frameworks (e.g. Strands, LangGraph, PydanticAI) for multi-step tasks.',
        courses: ['C2'],
        labs: ['L4', 'L6'],
      },
    ],
  },
  {
    id: 2,
    title: 'Applications and Integration',
    skills: [
      {
        id: '2.1',
        title: 'Understanding Requirements',
        weight: 3.4,
        summary:
          'Functional and infrastructure requirements derived from business requirements and solution architecture.',
        courses: ['C3', 'C5'],
        labs: ['L10'],
      },
      {
        id: '2.2',
        title: 'Systems Life Cycle',
        weight: 2.8,
        summary:
          'Life cycle concepts and frameworks to develop, implement, operate and maintain IT systems.',
        courses: ['C5'],
        labs: ['L10'],
      },
      {
        id: '2.3',
        title: 'Claude API Mechanics',
        weight: 6.8,
        summary:
          'Messages, tools, streaming, vision, thinking, caching, invoking Claude via third-party vendors, Messages API data access patterns, Batch API, and realtime vs. batch tradeoffs.',
        courses: ['C1', 'C2'],
        labs: ['L1', 'L2', 'L3'],
      },
      {
        id: '2.4',
        title: 'Software Engineering Foundations',
        weight: 7.4,
        summary:
          'REST APIs, JSON, asynchronous programming, version control, SDLC integration, code review, and small- and large-scale refactoring.',
        courses: ['C1', 'C3'],
        labs: ['L1', 'L4', 'L5', 'L7'],
      },
      {
        id: '2.5',
        title: 'Claude Application Design',
        weight: 8.6,
        summary:
          'How Claude interprets instructions across interfaces (Claude Code, Desktop, claude.ai, API, SDKs), content boundaries, schema design, session hygiene, and plugin management.',
        courses: ['C2', 'C3'],
        labs: ['L1', 'L7'],
      },
      {
        id: '2.6',
        title: 'Configuration Management',
        weight: 4.1,
        summary:
          'CLAUDE.md files, settings.json, model version pinning, prompt versioning, and plugin dependencies.',
        courses: ['C3', 'C5'],
        labs: ['L7', 'L10'],
      },
    ],
  },
  {
    id: 3,
    title: 'Claude Code',
    skills: [
      {
        id: '3.1',
        title: 'Claude Code Operation',
        weight: 3.1,
        summary:
          'Core components (Rules, Skills, Commands, Agents, Agent Memory), session management, built-in and custom slash commands, headless/streaming/auto mode, the CLAUDE.md hierarchy, repo initialization, and settings.json.',
        courses: ['C3'],
        labs: ['L7'],
      },
    ],
  },
  {
    id: 4,
    title: 'Eval, Testing, and Debugging',
    skills: [
      {
        id: '4.1',
        title: 'Debugging and Error Handling',
        weight: 2.6,
        summary:
          'Error type identification, recovery strategy selection, trace analysis to find failure modes, and isolating problems between the integration layer and model output.',
        courses: ['C4'],
        labs: ['L9'],
      },
    ],
  },
  {
    id: 5,
    title: 'Model Selection and Optimization',
    skills: [
      {
        id: '5.1',
        title: 'LLM Fundamentals',
        weight: 5.2,
        summary:
          'Tokens, context windows, sampling, non-determinism, next-token generation; fast mode, extended and adaptive thinking, effort levels; zero-, single- and multi-shot prompting.',
        courses: ['C1'],
        labs: ['L1'],
      },
      {
        id: '5.2',
        title: 'Technical Fundamentals',
        weight: 6.1,
        summary:
          'Foundational engineering for AI apps, such as integrating with SDKs that wrap REST APIs, and websockets.',
        courses: ['C1'],
        labs: ['L1', 'L5'],
      },
      {
        id: '5.3',
        title: 'Model Selection and Tradeoffs',
        weight: 2.7,
        summary:
          'Opus vs. Sonnet vs. Haiku use cases, adaptive thinking support, quality/latency/cost tradeoffs, and breaking behavior changes across model releases.',
        courses: ['C1', 'C5'],
        labs: ['L2'],
      },
      {
        id: '5.4',
        title: 'Cost and Token Management',
        weight: 2.8,
        summary:
          'Token budgeting, usage tracking, cost modeling, and caching techniques (prompt caching, cache check-pointing).',
        courses: ['C4'],
        labs: ['L2'],
      },
    ],
  },
  {
    id: 6,
    title: 'Prompt and Context Engineering',
    skills: [
      {
        id: '6.1',
        title: 'Context Engineering',
        weight: 3.8,
        summary:
          'Context window management, preventing context drift and bloat (tool output pruning, compaction), and context isolation via subagents or multi-step workflows.',
        courses: ['C2'],
        labs: ['L4', 'L6'],
      },
      {
        id: '6.2',
        title: 'Prompt Engineering',
        weight: 4.6,
        summary:
          'Instruction clarity, few-shot examples, system vs. user placement, output constraints, instruction placement across components, iterative refinement, and input sanitization.',
        courses: ['C2'],
        labs: ['L1'],
      },
      {
        id: '6.3',
        title: 'Output Handling',
        weight: 2.6,
        summary:
          'Structured output patterns, response validation, defensive parsing, and skepticism toward confident output.',
        courses: ['C2'],
        labs: ['L1', 'L9'],
      },
    ],
  },
  {
    id: 7,
    title: 'Security and Safety',
    skills: [
      {
        id: '7.1',
        title: 'AI Application Security',
        weight: 3.2,
        summary:
          'Prompt injection and jailbreak defense, untrusted input handling, data leakage prevention, PII handling, and authN/authZ, confidentiality and integrity.',
        courses: ['C4'],
        labs: ['L8'],
      },
      {
        id: '7.2',
        title: 'Guardrails and Safe Deployment',
        weight: 2.3,
        summary:
          'Content policy, guardrail layering, and secure-by-design principles (privacy, IAM, least privilege).',
        courses: ['C4'],
        labs: ['L8'],
      },
      {
        id: '7.3',
        title: 'Claude Hooks',
        weight: 1.0,
        summary: 'Using hooks as guardrails and safety controls to prevent destructive actions.',
        courses: ['C3'],
        labs: ['L6', 'L7'],
      },
      {
        id: '7.4',
        title: 'Identity, Secrets, and Key Management',
        weight: 1.6,
        summary:
          'Managing secrets, credentials and API keys across dev and prod; identity validation, access approval and level verification, and authorized access monitoring.',
        courses: ['C3', 'C4'],
        labs: ['L8', 'L10'],
      },
    ],
  },
  {
    id: 8,
    title: 'Tools and MCPs',
    skills: [
      {
        id: '8.1',
        title: 'Tool Implementation',
        weight: 4.4,
        summary:
          'Tool use and function calling, tool descriptions, error handling, agentic harness dispatch, client- vs. server-side tools, approval patterns, and tool set construction.',
        courses: ['C2'],
        labs: ['L4'],
      },
      {
        id: '8.2',
        title: 'MCP Server Development',
        weight: 2.1,
        summary:
          'Authoring and deploying MCP servers, integrating them with Claude apps, MCP resources/tools/prompts, and communication patterns (stdio, sockets, client vs. server).',
        courses: ['C3'],
        labs: ['L5'],
      },
      {
        id: '8.3',
        title: 'Agentic Customization',
        weight: 4.1,
        summary:
          'Tradeoffs among built-in tools, custom tools, Skills and MCPs, and choosing the right approach for a use case.',
        courses: ['C3'],
        labs: ['L5', 'L7'],
      },
    ],
  },
]

export const SKILLS: Skill[] = DOMAINS.flatMap((d) => d.skills)

const skillIndex = new Map(SKILLS.map((s) => [s.id, s]))

export function getSkill(id: string): Skill | undefined {
  return skillIndex.get(id)
}

export function domainOf(skillId: string): Domain | undefined {
  return DOMAINS.find((d) => d.id === Number(skillId.split('.')[0]))
}

export function domainWeight(domain: Domain): number {
  return round1(domain.skills.reduce((sum, s) => sum + s.weight, 0))
}

/** Target size of each skill's question pool: ~3× weight, minimum 6 (see PLAN.md §2). */
export function questionTarget(skill: Skill): number {
  return Math.max(6, Math.round(skill.weight * 3))
}

/**
 * Split `total` mock-exam items across skills proportionally to weight
 * (largest-remainder method), so the result always sums to exactly `total`.
 */
export function allocateItems(total: number = EXAM_FORMAT.items): Map<string, number> {
  const totalWeight = SKILLS.reduce((sum, s) => sum + s.weight, 0)
  const shares = SKILLS.map((s) => {
    const exact = (s.weight / totalWeight) * total
    return { id: s.id, base: Math.floor(exact), remainder: exact - Math.floor(exact) }
  })
  let leftover = total - shares.reduce((sum, s) => sum + s.base, 0)
  const byRemainder = [...shares].sort((a, b) => b.remainder - a.remainder)
  for (const share of byRemainder) {
    if (leftover === 0) break
    share.base += 1
    leftover -= 1
  }
  return new Map(shares.map((s) => [s.id, s.base]))
}

function round1(n: number): number {
  return Math.round(n * 10) / 10
}
