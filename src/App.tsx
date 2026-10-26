import { lazy, Suspense } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router'

// Every page is code-split: lessons and the question bank are the bulk of the bundle,
// so the shell loads fast and each content chunk loads on first use.
const BlueprintPage = lazy(() => import('./pages/BlueprintPage'))
const LearnPage = lazy(() => import('./pages/LearnPage'))
const PracticePage = lazy(() => import('./pages/PracticePage'))
const MockExamPage = lazy(() => import('./pages/MockExamPage'))
const LabsPage = lazy(() => import('./pages/LabsPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const QuestionsPage = lazy(() => import('./pages/QuestionsPage'))
const GuidePage = lazy(() => import('./pages/GuidePage'))

const NAV = [
  { to: '/', label: 'Playbook' },
  { to: '/learn', label: 'Learn' },
  { to: '/practice', label: 'Practice' },
  { to: '/questions', label: 'Questions' },
  { to: '/mock', label: 'Mock exam' },
  { to: '/labs', label: 'Labs' },
  { to: '/guides/cheat-sheet', label: 'Cheat sheet' },
  { to: '/guides/exam-day', label: 'Exam day' },
  { to: '/progress', label: 'Scoreboard' },
]

export default function App() {
  return (
    <div className="min-h-screen bg-page text-neutral-900">
      <header className="bg-header text-chalk print:hidden">
        <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">
            🏈 Gridiron Prep
          </Link>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => (isActive ? 'font-semibold underline underline-offset-4' : 'text-chalk/80')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Suspense fallback={<p className="text-neutral-500">Loading…</p>}>
          <Routes>
            <Route path="/" element={<BlueprintPage />} />
            <Route path="/learn" element={<LearnPage />} />
            <Route path="/learn/:skillId" element={<LearnPage />} />
            <Route path="/practice" element={<PracticePage />} />
            <Route path="/questions" element={<QuestionsPage />} />
            <Route path="/questions/:questionId" element={<QuestionsPage />} />
            <Route path="/mock" element={<MockExamPage />} />
            <Route path="/labs" element={<LabsPage />} />
            <Route path="/progress" element={<DashboardPage />} />
            <Route path="/labs/:labId" element={<LabsPage />} />
            <Route path="/guides/:slug" element={<GuidePage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
