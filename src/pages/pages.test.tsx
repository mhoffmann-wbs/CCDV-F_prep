import { render, screen, waitForElementToBeRemoved, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import App from '../App'
import { EXAM_FORMAT, SKILLS } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { getProgress, recordAnswer, resetProgress } from '../progress/store'

/** Renders the app at `path` and waits for the lazy-loaded page to replace the fallback. */
async function renderAt(path: string) {
  const result = render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
  if (screen.queryByText('Loading…')) await waitForElementToBeRemoved(() => screen.queryByText('Loading…'))
  return result
}

function escapeRegExp(text: string) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

beforeEach(() => {
  localStorage.clear()
  resetProgress()
})

describe('practice', () => {
  it('gives immediate feedback and records the attempt', async () => {
    const user = userEvent.setup()
    await renderAt('/practice?skill=7.1')
    // The session is shuffled, so find whichever question is showing.
    const shown = QUESTIONS.filter((q) => q.skillId === '7.1').find((q) => screen.queryByText(q.stem))!
    expect(shown).toBeDefined()

    const wrong = shown.options.filter((o) => !shown.correct.includes(o.id)).slice(0, shown.selectCount)
    for (const option of wrong) {
      await user.click(screen.getByRole(shown.selectCount > 1 ? 'checkbox' : 'radio', { name: new RegExp(escapeRegExp(option.text)) }))
    }
    await user.click(screen.getByRole('button', { name: 'Check answer' }))

    expect(screen.getByText(wrong[0].explanation)).toBeInTheDocument()
    expect(getProgress().questions[shown.id]).toMatchObject({ attempts: 1, correct: 0 })
  })

  it('limits multiple-response items to the stated number of selections', async () => {
    const user = userEvent.setup()
    await renderAt('/practice?skill=2.3')
    // Advance until the multi-select tool-results item is shown.
    for (let i = 0; i < 20 && !screen.queryByText('Select TWO.'); i++) {
      await user.click(screen.getAllByRole('radio')[0])
      await user.click(screen.getByRole('button', { name: 'Check answer' }))
      await user.click(screen.getByRole('button', { name: /Next play|Finish/ }))
    }
    const boxes = screen.getAllByRole('checkbox')
    await user.click(boxes[0])
    await user.click(boxes[1])
    await user.click(boxes[2])
    expect(boxes.filter((b) => (b as HTMLInputElement).checked)).toHaveLength(2)
  })

  it('runs an untimed mixed scrimmage across domains with immediate feedback', async () => {
    const user = userEvent.setup()
    await renderAt('/practice')
    await user.click(screen.getByRole('link', { name: '10 questions' }))
    expect(screen.getByText('Mixed scrimmage')).toBeInTheDocument()
    expect(screen.getByText(/Question 1 of 10/)).toBeInTheDocument()
    expect(screen.queryByLabelText('time remaining')).not.toBeInTheDocument()

    const shown = QUESTIONS.find((q) => screen.queryByText(q.stem))!
    const pick = shown.options.slice(0, shown.selectCount)
    for (const option of pick) {
      await user.click(screen.getByRole(shown.selectCount > 1 ? 'checkbox' : 'radio', { name: new RegExp(escapeRegExp(option.text)) }))
    }
    await user.click(screen.getByRole('button', { name: 'Check answer' }))
    expect(screen.getByText(pick[0].explanation)).toBeInTheDocument()
    expect(getProgress().questions[shown.id]).toMatchObject({ attempts: 1 })

    // Play out the rest of the set; the end screen breaks the score down by domain.
    await user.click(screen.getByRole('button', { name: 'Next play' }))
    for (let i = 1; i < 10; i++) {
      const current = QUESTIONS.find((q) => screen.queryByText(q.stem))!
      const role = current.selectCount > 1 ? 'checkbox' : 'radio'
      for (const box of screen.getAllByRole(role).slice(0, current.selectCount)) await user.click(box)
      await user.click(screen.getByRole('button', { name: 'Check answer' }))
      await user.click(screen.getByRole('button', { name: /Next play|Finish/ }))
    }
    expect(screen.getByText(/Drive complete: Mixed scrimmage/)).toBeInTheDocument()
    expect(screen.getByText(/\/ 10 correct/)).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Domain' })).toBeInTheDocument()
    expect(getProgress().mockResults).toHaveLength(0)

    // Running it again starts a fresh set of the same kind straight away.
    await user.click(screen.getByRole('button', { name: 'Run it again' }))
    expect(screen.getByText('Question 1 of 10 · 0/0 correct')).toBeInTheDocument()
    expect(screen.getByText('Mixed scrimmage')).toBeInTheDocument()
  })

  it('runs a least-mastered scrimmage that picks unmastered questions within each topic', async () => {
    const user = userEvent.setup()
    // Leave five questions per skill unmastered: more than a 10-item set draws from one skill.
    const unmastered = new Set(SKILLS.flatMap((s) => QUESTIONS.filter((q) => q.skillId === s.id).slice(0, 5).map((q) => q.id)))
    for (const q of QUESTIONS) if (!unmastered.has(q.id)) recordAnswer(q.id, true)
    await renderAt('/practice')
    await user.click(screen.getByRole('button', { name: 'Least mastered' }))
    await user.click(screen.getByRole('link', { name: '10 questions' }))
    expect(screen.getByText('Mixed scrimmage: least mastered')).toBeInTheDocument()
    const shown = QUESTIONS.find((q) => screen.queryByText(q.stem))!
    expect(unmastered.has(shown.id)).toBe(true)
  })

  it('starts a least-mastered skill session with the questions not yet answered correctly', async () => {
    const user = userEvent.setup()
    const pool = QUESTIONS.filter((q) => q.skillId === '7.3')
    const unmastered = pool.slice(0, 2).map((q) => q.id)
    for (const q of pool) if (!unmastered.includes(q.id)) recordAnswer(q.id, true)
    await renderAt('/practice')
    await user.click(screen.getByRole('button', { name: 'Least mastered' }))
    await user.click(screen.getByRole('link', { name: /7\.3 Claude Hooks/ }))
    expect(screen.getByText(new RegExp(`Question 1 of ${pool.length}`))).toBeInTheDocument()
    expect(screen.getByText(/: least mastered$/)).toBeInTheDocument()
    expect(unmastered).toContain(pool.find((q) => screen.queryByText(q.stem))!.id)
  })
  it('ends with a review that lists the misses first', async () => {
    const user = userEvent.setup()
    await renderAt('/practice?skill=7.3')
    const pool = QUESTIONS.filter((q) => q.skillId === '7.3')
    let missed: string | undefined
    for (let i = 0; i < pool.length; i++) {
      const current = pool.find((q) => screen.queryByText(q.stem))!
      // Miss the last question so the review has to reorder it to the top.
      const last = i === pool.length - 1
      const pick = current.options.filter((o) => current.correct.includes(o.id) !== last).slice(0, current.selectCount)
      for (const option of pick) {
        await user.click(screen.getByRole(current.selectCount > 1 ? 'checkbox' : 'radio', { name: new RegExp(escapeRegExp(option.text)) }))
      }
      await user.click(screen.getByRole('button', { name: 'Check answer' }))
      await user.click(screen.getByRole('button', { name: /Next play|Finish/ }))
      if (last) missed = current.stem
    }
    expect(screen.getByRole('heading', { name: 'Film review' })).toBeInTheDocument()
    const marks = screen.getAllByLabelText(/^(correct|missed)$/)
    expect(marks).toHaveLength(pool.length)
    expect(marks[0]).toHaveAccessibleName('missed')
    expect(marks.slice(1).every((m) => m.getAttribute('aria-label') === 'correct')).toBe(true)
    expect(marks[0].nextElementSibling).toHaveTextContent(missed!)
  })
})

describe('question bank', () => {
  it('filters by topic and mastery and lets a question be answered on its own', async () => {
    const user = userEvent.setup()
    const [missed, ...rest] = QUESTIONS.filter((q) => q.skillId === '7.3')
    recordAnswer(missed.id, false)
    await renderAt('/questions?skill=7.3')
    expect(screen.getAllByRole('link', { name: /Not tested/ })).toHaveLength(rest.length)

    await user.click(screen.getByRole('button', { name: 'Recent error (1)' }))
    const links = screen.getAllByRole('link', { name: /Recent error/ })
    expect(links).toHaveLength(1)
    await user.click(links[0])

    expect(screen.getByText(missed.stem)).toBeInTheDocument()
    const role = missed.selectCount > 1 ? 'checkbox' : 'radio'
    for (const option of missed.options.filter((o) => missed.correct.includes(o.id))) {
      await user.click(screen.getByRole(role, { name: new RegExp(escapeRegExp(option.text)) }))
    }
    await user.click(screen.getByRole('button', { name: 'Check answer' }))
    expect(screen.getByText('Past error, since correct')).toBeInTheDocument()
    expect(getProgress().questions[missed.id]).toMatchObject({ attempts: 2, correct: 1, lastCorrect: true })
  })
})

describe('mock exam', () => {
  it('runs from intro to a score report with per-domain results', async () => {
    const user = userEvent.setup()
    await renderAt('/mock')
    await user.click(screen.getByRole('button', { name: 'Kick off' }))
    const examLength = Math.min(QUESTIONS.length, EXAM_FORMAT.items)
    for (let i = 1; i < examLength; i++) {
      await user.click(screen.getByRole('button', { name: 'Next' }))
    }
    await user.click(screen.getByRole('button', { name: 'Review' }))
    expect(screen.getByText(new RegExp(`${examLength} item\\(s\\) unanswered`))).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Submit exam' }))

    expect(screen.getByText(/Estimated scaled score/)).toBeInTheDocument()
    expect(screen.getByText('2. Applications and Integration')).toBeInTheDocument()
    expect(getProgress().mockResults).toHaveLength(1)

    // A new exam starts at once, skipping the intro, with nothing carried over.
    await user.click(screen.getByRole('button', { name: 'Start a new mock exam' }))
    expect(screen.getByText(`Item 1 of ${examLength}`)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Flag for review' }))
    expect(screen.getByRole('button', { name: 'Unflag' })).toBeInTheDocument()
  })
})

describe('learn', () => {
  it('renders a lesson with its sections and tracks read state', async () => {
    const user = userEvent.setup()
    await renderAt('/learn/2.5')
    // The Learn route is code-split, so wait for it to load.
    expect(
      await screen.findByRole('heading', { level: 1, name: /2.5 Claude Application Design/ }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Exam traps' })).toBeInTheDocument()
    expect(screen.getByRole('table')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Mark as read' }))
    expect(getProgress().lessonsRead).toEqual(['2.5'])
    await user.click(screen.getByRole('button', { name: /Marked as read/ }))
    expect(getProgress().lessonsRead).toEqual([])
  })

  it('links each lesson to the previous and next topic in blueprint order', async () => {
    const user = userEvent.setup()
    await renderAt('/learn/2.5')
    const nav = screen.getByRole('navigation', { name: 'Lesson navigation' })
    expect(within(nav).getByRole('link', { name: /Previous topic.*2\.4/ })).toHaveAttribute('href', '/learn/2.4')
    await user.click(within(nav).getByRole('link', { name: /Next topic.*2\.6/ }))
    expect(await screen.findByRole('heading', { level: 1, name: /2\.6 / })).toBeInTheDocument()
  })

  it('has no previous topic on the first lesson', async () => {
    await renderAt(`/learn/${SKILLS[0].id}`)
    const nav = screen.getByRole('navigation', { name: 'Lesson navigation' })
    expect(within(nav).queryByText(/Previous topic/)).not.toBeInTheDocument()
    expect(within(nav).getByText(/Next topic/)).toBeInTheDocument()
  })
})

describe('guides', () => {
  it('renders the cheat sheet with a section per domain', async () => {
    await renderAt('/guides/cheat-sheet')
    expect(screen.getByRole('heading', { level: 1, name: 'Cheat sheet' })).toBeInTheDocument()
    for (const domain of ['1. Agents and workflows', '5. Model selection and optimization', '8. Tools and MCP']) {
      expect(screen.getByRole('heading', { level: 2, name: domain })).toBeInTheDocument()
    }
  })
})

describe('labs', () => {
  it('shows a lab with its checklist and saves ticked steps', async () => {
    const user = userEvent.setup()
    await renderAt('/labs/L1')
    expect(screen.getByRole('heading', { level: 1, name: /L1: Play-by-play summarizer/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Done when' })).toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: /Count input tokens/ }))
    expect(getProgress().labSteps.L1).toEqual(['tokens'])
    expect(screen.getByText('Checklist (1/6)')).toBeInTheDocument()
  })

  it('links the playbook lab tags to their lab pages', async () => {
    const user = userEvent.setup()
    await renderAt('/')
    await user.click(screen.getAllByRole('link', { name: /^L1: / })[0])
    expect(await screen.findByRole('heading', { level: 1, name: /L1: Play-by-play summarizer/ })).toBeInTheDocument()
  })
})

describe('scoreboard', () => {
  it('shows readiness and links to the weak-area drill', async () => {
    const user = userEvent.setup()
    await renderAt('/progress')
    expect(screen.getByText('Weighted readiness')).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Run the weak-area drill' }))
    expect(await screen.findByText('Weak-area drill')).toBeInTheDocument()
  })
})
