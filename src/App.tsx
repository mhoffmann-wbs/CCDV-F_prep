import { Link, Route, Routes } from 'react-router'
import BlueprintPage from './pages/BlueprintPage'

export default function App() {
  return (
    <div className="min-h-screen bg-chalk text-neutral-900">
      <header className="bg-field-dark text-chalk">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <Link to="/" className="text-lg font-bold tracking-tight">
            🏈 Gridiron Prep
          </Link>
          <span className="text-sm text-chalk/70">CCDV-F exam prep</span>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<BlueprintPage />} />
        </Routes>
      </main>
    </div>
  )
}
