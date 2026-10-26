/** One line listing the shortcuts a screen supports. Hidden on phones, which have no keyboard. */
export default function ShortcutHint({ items }: { items: [keys: string, action: string][] }) {
  return (
    <p className="hidden text-xs text-neutral-500 sm:block">
      Keyboard:{' '}
      {items.map(([keys, action], i) => (
        <span key={keys}>
          {i > 0 && ' · '}
          <kbd className="rounded border border-neutral-300 px-1 font-mono">{keys}</kbd> {action}
        </span>
      ))}
    </p>
  )
}
