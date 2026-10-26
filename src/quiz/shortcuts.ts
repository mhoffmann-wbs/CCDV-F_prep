import { useEffect, useRef } from 'react'

/** Handlers keyed by `KeyboardEvent.key`, lowercased for single characters (e.g. "a", "1", "Enter"). */
export type ShortcutMap = Record<string, () => void>

// Keys typed into a text field are text, and Enter or Space on a focused button or link already clicks it.
function belongsToTarget(event: KeyboardEvent): boolean {
  const target = event.target
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return true
  if (target instanceof HTMLInputElement) return target.type !== 'radio' && target.type !== 'checkbox'
  return ['BUTTON', 'A'].includes(target.tagName) && (event.key === 'Enter' || event.key === ' ')
}

/** Binds keyboard shortcuts on the window while `enabled`. Handlers may change on every render. */
export function useShortcuts(handlers: ShortcutMap, enabled = true) {
  const latest = useRef(handlers)
  useEffect(() => {
    latest.current = handlers
  })
  useEffect(() => {
    if (!enabled) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return
      if (belongsToTarget(event)) return
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key
      const handler = latest.current[key]
      if (!handler) return
      event.preventDefault()
      handler()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled])
}
