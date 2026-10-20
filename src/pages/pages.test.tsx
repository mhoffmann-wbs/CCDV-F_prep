import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import App from '../App'
import { EXAM_FORMAT } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { getProgress, resetProgress } from '../progress/store'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
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
    renderAt('/practice?skill=7.1')
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
    renderAt('/practice?skill=2.3')
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
})

describe('mock exam', () => {
  it('runs from intro to a score report with per-domain results', async () => {
    const user = userEvent.setup()
    renderAt('/mock')
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
  })
})

describe('learn', () => {
  it('renders a lesson with its sections and tracks read state', async () => {
    const user = userEvent.setup()
    renderAt('/learn/2.5')
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
})
