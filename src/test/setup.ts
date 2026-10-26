import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest runs without globals, so Testing Library can't register its own auto-cleanup.
afterEach(() => cleanup())

// jsdom doesn't implement scrolling; lesson pages scroll to the top on navigation.
// Return a value like Chrome does, so an effect that returns scrollTo's result fails in tests too.
window.scrollTo = () => Promise.resolve() as unknown as void
