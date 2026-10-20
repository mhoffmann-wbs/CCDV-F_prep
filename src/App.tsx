import { lazy, Suspense } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router'
import BlueprintPage from './pages/BlueprintPage'
import MockExamPage from './pages/MockExamPage'
import PracticePage from './pages/PracticePage'

// Lessons are the bulk of the bundle, so the Learn section is code-split.
const LearnPage = lazy(() => import('./pages/LearnPage'))

const NAV = [
  { to: '/', label: 'Playbook' },
  { to: '/learn', label: 'Learn' },
  { to: '/practice', label: 'Practice' },
  { to: '/mock', label: 'Mock exam' },
]

export default function App() {
  return (
    <div className="min-h-screen bg-chalk text-neutral-900">
      <header className="bg-field-dark text-chalk">
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
            <Route path="/mock" element={<MockExamPage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
