import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import App from '../App'
import { QUESTIONS } from '../content/questions'
import { getProgress, resetProgress } from '../progress/store'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  localStorage.clear()
  resetProgress()
})

describe('practice', () => {
  it('gives immediate feedback and records the attempt', async () => {
    const user = userEvent.setup()
    renderAt('/practice?skill=7.1')
    const official = QUESTIONS.find((q) => q.id === 'official-2')!
    expect(screen.getByText(official.stem)).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /Raise the model's temperature/ }))
    await user.click(screen.getByRole('button', { name: 'Check answer' }))

    expect(screen.getByText(/Temperature is irrelevant to prompt injection/)).toBeInTheDocument()
    expect(getProgress().questions['official-2']).toMatchObject({ attempts: 1, correct: 0 })
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
    for (let i = 1; i < QUESTIONS.length; i++) {
      await user.click(screen.getByRole('button', { name: 'Next' }))
    }
    await user.click(screen.getByRole('button', { name: 'Review' }))
    expect(screen.getByText(new RegExp(`${QUESTIONS.length} item\\(s\\) unanswered`))).toBeInTheDocument()
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
