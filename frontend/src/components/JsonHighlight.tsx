/**
 * Renders pretty-printed JSON with syntax highlighting (keys, strings, numbers, etc.).
 * Use in a <pre> or scrollable block for readable, colorized output.
 */

type TokenType = 'key' | 'string' | 'number' | 'boolean' | 'null' | 'punctuation'

type Token = { type: TokenType; value: string }

const KEY_CLASS = 'text-[var(--lagoon-deep)] font-medium'
const STRING_CLASS = 'text-[var(--sea-ink)]'
const NUMBER_CLASS = 'text-[var(--palm)]'
const BOOLEAN_CLASS = 'text-[var(--lagoon)]'
const NULL_CLASS = 'text-[var(--sea-ink-soft)]'
const PUNCT_CLASS = 'text-[var(--sea-ink-soft)]'

/** Tokenize a pretty-printed JSON string for syntax highlighting. */
function tokenize(jsonStr: string): Token[] {
  const tokens: Token[] = []
  let i = 0
  const n = jsonStr.length

  while (i < n) {
    const rest = jsonStr.slice(i)

    // Whitespace (keep as single token for rendering)
    const wsMatch = rest.match(/^(\s+)/)
    if (wsMatch) {
      tokens.push({ type: 'punctuation', value: wsMatch[1] })
      i += wsMatch[1].length
      continue
    }

    // Punctuation
    if (/^[{}[\],:]/.test(rest)) {
      tokens.push({ type: 'punctuation', value: rest[0] })
      i += 1
      continue
    }

    // String (handles escaped quotes); key if followed by optional space and colon
    const strMatch = rest.match(/^"((?:[^"\\]|\\.)*)"/)
    if (strMatch) {
      const full = strMatch[0]
      const after = jsonStr.slice(i + full.length)
      const isKey = /^\s*:/.test(after)
      tokens.push({
        type: isKey ? 'key' : 'string',
        value: full,
      })
      i += full.length
      continue
    }

    // Number
    const numMatch = rest.match(/^-?\d+\.?\d*([eE][+-]?\d+)?/)
    if (numMatch) {
      tokens.push({ type: 'number', value: numMatch[0] })
      i += numMatch[0].length
      continue
    }

    // true / false / null
    if (rest.startsWith('true')) {
      tokens.push({ type: 'boolean', value: 'true' })
      i += 4
      continue
    }
    if (rest.startsWith('false')) {
      tokens.push({ type: 'boolean', value: 'false' })
      i += 5
      continue
    }
    if (rest.startsWith('null')) {
      tokens.push({ type: 'null', value: 'null' })
      i += 4
      continue
    }

    // Fallback: single char (shouldn't happen in valid JSON)
    tokens.push({ type: 'punctuation', value: rest[0] ?? '' })
    i += 1
  }

  return tokens
}

function tokenToClassName(type: TokenType): string {
  switch (type) {
    case 'key':
      return KEY_CLASS
    case 'string':
      return STRING_CLASS
    case 'number':
      return NUMBER_CLASS
    case 'boolean':
      return BOOLEAN_CLASS
    case 'null':
      return NULL_CLASS
    case 'punctuation':
      return PUNCT_CLASS
  }
}

type JsonHighlightProps = {
  /** Object or already stringified JSON. Will be pretty-printed with 2 spaces if object. */
  data: unknown
  className?: string
}

export function JsonHighlight({ data, className = '' }: JsonHighlightProps) {
  const str =
    typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  const tokens = tokenize(str)

  return (
    <pre
      className={`overflow-auto text-sm font-mono max-h-[400px] whitespace-pre-wrap break-words ${className}`}
    >
      {tokens.map((t, idx) => (
        <span key={idx} className={t.type === 'punctuation' && /^\s+$/.test(t.value) ? undefined : tokenToClassName(t.type)}>
          {t.value}
        </span>
      ))}
    </pre>
  )
}
