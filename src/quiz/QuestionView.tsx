import type { Question } from '../content/schema'
import { getSkill } from '../content/blueprint'
import { useShortcuts, type ShortcutMap } from './shortcuts'

const COUNT_WORDS = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE']

interface Props {
  question: Question
  selected: readonly string[]
  onChange: (selected: string[]) => void
  /** When true, inputs lock and every option's explanation is shown. */
  revealed?: boolean
  /** Select options with 1–6 or A–F. Only one QuestionView on screen should enable this. */
  keyboard?: boolean
}

export default function QuestionView({ question, selected, onChange, revealed = false, keyboard = false }: Props) {
  const multi = question.selectCount > 1
  const skill = getSkill(question.skillId)!

  function toggle(id: string) {
    if (revealed) return
    if (!multi) return onChange([id])
    if (selected.includes(id)) return onChange(selected.filter((s) => s !== id))
    // Like the real exam, don't allow more selections than the item asks for.
    if (selected.length < question.selectCount) onChange([...selected, id])
  }

  const optionKeys: ShortcutMap = {}
  question.options.forEach((option, i) => {
    optionKeys[String(i + 1)] = () => toggle(option.id)
    optionKeys[option.id.toLowerCase()] = () => toggle(option.id)
  })
  useShortcuts(optionKeys, keyboard && !revealed)

  return (
    <article className="space-y-4">
      <p className="text-xs uppercase tracking-wide text-neutral-500">
        {skill.id} {skill.title}
        {question.official && (
          <span className="ml-2 rounded bg-field px-1.5 py-0.5 normal-case text-chalk">
            Official sample
          </span>
        )}
      </p>
      <p className="text-lg leading-relaxed">{question.stem}</p>
      <p className="text-sm font-medium text-neutral-600">
        {multi ? `Select ${COUNT_WORDS[question.selectCount - 1]}.` : 'Select ONE.'}
      </p>

      <fieldset className="space-y-2">
        <legend className="sr-only">Answer options</legend>
        {question.options.map((option) => {
          const isSelected = selected.includes(option.id)
          const isKey = question.correct.includes(option.id)
          const tone = !revealed
            ? isSelected
              ? 'border-field bg-field/5'
              : 'border-neutral-200 bg-white hover:border-neutral-400'
            : isKey
              ? 'border-green-600 bg-green-50'
              : isSelected
                ? 'border-red-600 bg-red-50'
                : 'border-neutral-200 bg-white opacity-80'
          return (
            <label
              key={option.id}
              className={`block cursor-pointer rounded-lg border-2 p-3 transition-colors ${tone}`}
            >
              <span className="flex gap-3">
                <input
                  type={multi ? 'checkbox' : 'radio'}
                  name={question.id}
                  value={option.id}
                  checked={isSelected}
                  disabled={revealed}
                  onChange={() => toggle(option.id)}
                  className="mt-1 accent-field"
                />
                <span>
                  <span className="mr-2 font-semibold">{option.id}.</span>
                  {option.text}
                </span>
              </span>
              {revealed && (
                <span className="mt-2 block pl-7 text-sm text-neutral-700">
                  <span className="font-semibold">{isKey ? '✓ ' : '✗ '}</span>
                  {option.explanation}
                </span>
              )}
            </label>
          )
        })}
      </fieldset>

      {revealed && (
        <p className="text-sm text-neutral-600">
          Learn more:{' '}
          {question.sourceLinks.map((url, i) => (
            <span key={url}>
              {i > 0 && ' · '}
              <a href={url} target="_blank" rel="noreferrer" className="underline">
                {new URL(url).hostname === 'platform.claude.com'
                  ? url.split('/').pop()
                  : new URL(url).hostname}
              </a>
            </span>
          ))}
        </p>
      )}
    </article>
  )
}
