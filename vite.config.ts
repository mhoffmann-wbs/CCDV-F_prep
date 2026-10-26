import mdx from '@mdx-js/rollup'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import remarkGfm from 'remark-gfm'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  // GitHub Pages serves the app under /<repo>/; the deploy workflow sets BASE_PATH. Everything else uses /.
  base: process.env.BASE_PATH ?? '/',
  plugins: [{ enforce: 'pre', ...mdx({ remarkPlugins: [remarkGfm] }) }, react({ include: /\.(mdx|tsx?)$/ }), tailwindcss()],
  build: {
    // The question bank is one ~550 kB data chunk (~160 kB gzipped) that practice and the mock
    // exam both need in full; splitting it further would only add requests.
    chunkSizeWarningLimit: 700,
  },
  test: {
    environment: 'jsdom',
    // labs/ is a separate npm workspace with its own tests (cd labs && npm test).
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['./src/test/setup.ts'],
  },
})
