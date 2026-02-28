import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  getMockContactById,
  getMockInteractions,
  getMockDecision,
  MOCK_LIVE_TRANSCRIPT,
  MOCK_DECISION_LOG,
  ACTION_LABELS,
  MOCK_CONTEXT_FILES,
} from '#/lib/mock'
import { UploadDropzone } from '#/lib/uploadthing'

export const Route = createFileRoute('/contacts/$contactId')({
  component: ContactDetailPage,
})

function ContactDetailPage() {
  const { contactId } = Route.useParams()
  const {
    data: contact,
    isPending,
    isError,
  } = useQuery({
    queryKey: ['contact', contactId],
    queryFn: () => Promise.resolve(getMockContactById(contactId)),
  })

  const interactions = contact ? getMockInteractions(contact.email) : []
  const decision = contact ? getMockDecision(contact.email) : undefined

  // Call state: live (after start), listening (user clicked Listen in) — mock only
  const [callLive, setCallLive] = useState(false)
  const [listening, setListening] = useState(false)
  const [intervened, setIntervened] = useState(false)

  // Files: mock list + any uploaded this session (from UploadThing onClientUploadComplete)
  const [uploadedFiles, setUploadedFiles] = useState<
    { name: string; url: string; key: string | null; size: number }[]
  >(MOCK_CONTEXT_FILES)

  const handleStartCall = () => {
    setCallLive(true)
    setListening(true)
    setIntervened(false)
  }

  if (!isPending && !contact) {
    return (
      <main className="page-wrap px-4 py-8">
        <p className="text-red-600">Contact not found.</p>
        <Link to="/" className="mt-4 inline-block text-[var(--lagoon)]">
          ← Back to contacts
        </Link>
      </main>
    )
  }

  if (!contact) {
    return (
      <main className="page-wrap px-4 py-8">
        <p className="text-[var(--sea-ink-soft)]">Loading…</p>
      </main>
    )
  }

  const profile = contact.behavior_profile ?? {}

  return (
    <main className="page-wrap px-4 py-8">
      <div className="mb-6 flex items-center gap-4">
        <Link to="/" className="text-[var(--lagoon)] hover:underline">
          ← Contacts
        </Link>
      </div>
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--sea-ink)]">
          {contact.name}
        </h1>
        <p className="text-[var(--sea-ink-soft)]">{contact.email}</p>
        {contact.risk_score != null && (
          <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
            Risk score: {contact.risk_score.toFixed(2)}
            {contact.trust_score != null &&
              ` · Trust score: ${contact.trust_score.toFixed(2)}`}
          </p>
        )}
      </header>

      <div className="mb-8 max-w-3xl">
        {typeof profile.psychological_profile === 'string' ? (
          <p className="text-base text-[var(--sea-ink)] leading-relaxed md:text-lg">
            {profile.psychological_profile}
          </p>
        ) : typeof profile.summary === 'string' ? (
          <p className="text-base text-[var(--sea-ink)] leading-relaxed md:text-lg">
            {profile.summary}
          </p>
        ) : (
          <p className="text-base text-[var(--sea-ink-soft)] leading-relaxed md:text-lg">
            No psychological profile yet. Communication patterns will be summarized here after enough interactions.
          </p>
        )}
      </div>

      {/* Call controls: Listen in call, Live indicator, Listen in / Intervene */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-[var(--sea-ink)]">
          Call
        </h2>
        {callLive && (
          <div className="mb-3 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-0.5 text-sm font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
              <span
                className="h-2 w-2 rounded-full bg-red-500 animate-pulse"
                aria-hidden
              />
              Live
            </span>
            <span className="text-sm text-[var(--sea-ink-soft)]">
              Call in progress
            </span>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {!callLive && (
            <button
              type="button"
              onClick={handleStartCall}
              className="flex items-center gap-2 rounded-lg bg-[var(--lagoon)] px-4 py-2 font-medium text-white hover:opacity-90"
            >
              Listen in call
              <span className="flex items-end gap-0.5" aria-label="Audio streaming">
                {[
                  { name: 'audio-bar-1', duration: 0.55 },
                  { name: 'audio-bar-2', duration: 0.7 },
                  { name: 'audio-bar-3', duration: 0.5 },
                  { name: 'audio-bar-4', duration: 0.65 },
                  { name: 'audio-bar-5', duration: 0.6 },
                ].map(({ name, duration }, i) => (
                  <span
                    key={i}
                    className="w-1 rounded-full bg-white/90 origin-bottom"
                    style={{
                      height: '10px',
                      animation: `${name} ${duration}s ease-in-out infinite`,
                      animationDelay: `${i * 0.12}s`,
                    }}
                  />
                ))}
              </span>
            </button>
          )}
          {callLive && listening && (
            <>
              <button
                type="button"
                onClick={() => setIntervened(true)}
                className={
                  intervened
                    ? 'intervene-glow rounded-lg border border-green-500 bg-green-50 px-4 py-2 font-medium text-green-800 dark:border-green-600 dark:bg-green-900/20 dark:text-green-200'
                    : 'rounded-lg border border-amber-500 bg-amber-50 px-4 py-2 font-medium text-amber-800 hover:bg-amber-100 dark:bg-amber-900/20 dark:text-amber-200'
                }
              >
                {intervened ? (
                  <>
                    Intervening
                    <span className="inline-flex">
                      <span className="intervene-dot-1">.</span>
                      <span className="intervene-dot-2">.</span>
                      <span className="intervene-dot-3">.</span>
                    </span>
                  </>
                ) : (
                  'Intervene'
                )}
              </button>
              <button
                type="button"
                onClick={() => {
                  setListening(false)
                  setCallLive(false)
                  setIntervened(false)
                }}
                className="rounded-lg border border-red-500 bg-red-50 px-4 py-2 font-medium text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:border-red-600 dark:text-red-300 dark:hover:bg-red-900/30"
              >
                Stop listening
              </button>
            </>
          )}
          {callLive && !listening && (
            <button
              type="button"
              onClick={() => setListening(true)}
              className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-2 font-medium text-[var(--sea-ink)] hover:bg-[var(--chip-bg)]"
            >
              Listen in
            </button>
          )}
        </div>
        {/* Thinking stream / decision log: only visible when listening */}
        {callLive && listening && (
          <div className="mt-4 space-y-4">
            <div className="rounded-xl border border-[var(--line)] bg-[var(--foam)] p-4">
              <h3 className="mb-2 text-sm font-medium text-[var(--sea-ink)]">
                Agent thinking
              </h3>
              <div className="max-h-48 overflow-auto font-mono text-sm text-[var(--sea-ink-soft)] whitespace-pre-wrap">
                {intervened
                  ? '-'
                  : MOCK_DECISION_LOG.map((e) => `[${e.ts}ms] ${e.event}`).join(
                      '\n',
                    )}
              </div>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-[var(--foam)] p-4">
              <h3 className="mb-2 text-sm font-medium text-[var(--sea-ink)]">
                Live transcript
              </h3>
              <div className="max-h-64 overflow-auto space-y-2 text-sm">
                {MOCK_LIVE_TRANSCRIPT.map((t) => (
                  <p key={t.ts}>
                    <span className="font-medium text-[var(--sea-ink)]">
                      {t.speaker}:
                    </span>{' '}
                    <span className="text-[var(--sea-ink-soft)]">{t.text}</span>
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Decision (mock) */}
      {decision && (
        <section className="mb-8">
          <h2 className="mb-3 text-lg font-semibold text-[var(--sea-ink)]">
            Decision
          </h2>
          <div className="rounded-xl border border-[var(--line)] bg-[var(--foam)] p-4 space-y-3">
            <p>
              <span className="text-sm font-medium text-[var(--sea-ink)]">
                Action:{' '}
              </span>
              <span className="text-sm text-[var(--sea-ink-soft)]">
                {ACTION_LABELS[decision.approach_chosen] ??
                  decision.approach_chosen}
              </span>
            </p>
            <p className="text-sm text-[var(--sea-ink-soft)]">
              {decision.reasoning}
            </p>
            <p className="text-sm">
              <span className="font-medium text-[var(--sea-ink)]">
                Confidence:{' '}
              </span>
              <span className="text-[var(--sea-ink-soft)]">
                {(decision.confidence_score * 100).toFixed(0)}%
              </span>
              {decision.escalate && (
                <span className="ml-2 text-amber-600">Escalate</span>
              )}
            </p>
            <details className="text-sm">
              <summary className="cursor-pointer text-[var(--lagoon)]">
                Pass 1 & 2 reasoning
              </summary>
              <p className="mt-2 text-[var(--sea-ink-soft)]">
                {decision.pass1_reasoning}
              </p>
              <p className="mt-2 text-[var(--sea-ink-soft)]">
                {decision.pass2_reasoning}
              </p>
            </details>
          </div>
        </section>
      )}

      {/* History (Interactions, mock) */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-[var(--sea-ink)]">
          History
        </h2>
        {interactions.length > 0 ? (
          <ul className="space-y-2">
            {interactions.map((i) => (
              <li
                key={i.id}
                className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2"
              >
                <span className="text-xs text-[var(--sea-ink-soft)]">
                  {new Date(i.timestamp).toLocaleString()}
                </span>
                <span className="ml-2 text-xs text-[var(--sea-ink-soft)]">
                  {i.type}
                </span>
                <p className="mt-1 text-sm text-[var(--sea-ink)]">
                  {i.summary}
                </p>
                {i.outcome && (
                  <span className="text-xs text-[var(--palm)]">
                    Outcome: {i.outcome}
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[var(--sea-ink-soft)]">
            No interactions yet.
          </p>
        )}
      </section>

      {/* Profile JSON (engineering description) */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-[var(--sea-ink)]">
          Behavioral profile (engineering)
        </h2>
        <div className="rounded-xl border border-[var(--line)] bg-[var(--foam)] p-4">
          <pre className="overflow-auto text-sm font-mono text-[var(--sea-ink)] max-h-[400px] whitespace-pre-wrap break-words">
            {JSON.stringify(profile, null, 2)}
          </pre>
        </div>
      </section>

      {/* Client context: upload via UploadThing */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-[var(--sea-ink)]">
          Client context
        </h2>
        <p className="mb-3 text-sm text-[var(--sea-ink-soft)]">
          Add context (PDF, CSV, Word, etc.) for this contact. Files are stored
          via UploadThing.
        </p>
        {uploadedFiles.length > 0 && (
          <div className="mb-4 space-y-2">
            <p className="text-sm font-medium text-[var(--sea-ink)]">
              Uploaded files
            </p>
            <ul className="space-y-2">
              {uploadedFiles.map((file) => (
                <li
                  key={file.key ?? file.url}
                  className="group flex items-center justify-between gap-2 rounded-md border border-[var(--line)] bg-[var(--surface)] px-3 py-1"
                >
                  <a
                    href={file.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="min-w-0 flex-1 truncate text-sm leading-snug text-[var(--lagoon)] hover:underline"
                  >
                    {file.name}
                  </a>
                  <span className="shrink-0 text-xs leading-snug text-[var(--sea-ink-soft)] transition-transform duration-200 ease-out group-hover:-translate-x-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setUploadedFiles((prev) =>
                        prev.filter(
                          (f) => (f.key && f.key !== file.key) || f.url !== file.url,
                        ),
                      )
                    }
                    className="h-0 min-h-0 max-w-0 shrink-0 overflow-hidden rounded px-0 py-0 text-xs font-medium leading-none text-red-600 opacity-0 transition-all duration-200 ease-out hover:bg-red-50 hover:text-red-700 group-hover:h-auto group-hover:min-h-0 group-hover:max-w-[5rem] group-hover:px-2 group-hover:py-0.5 group-hover:opacity-100 dark:hover:bg-red-900/20 dark:text-red-400 dark:hover:text-red-300"
                    aria-label={`Delete ${file.name}`}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <UploadDropzone
          endpoint="contextFile"
          className="mb-4 rounded-xl border-2 border-dashed border-[var(--line)] bg-[var(--foam)] p-8 transition-colors hover:border-[var(--lagoon)] hover:bg-[var(--surface)] ut-uploading:border-[var(--lagoon)] ut-uploading:bg-[var(--surface)]"
          onClientUploadComplete={(res) => {
            if (res?.length) {
              setUploadedFiles((prev) => [
                ...prev,
                ...res.map((f) => ({
                  name: f.name,
                  url: f.url,
                  key: f.key ?? null,
                  size: f.size,
                })),
              ])
            }
          }}
          onUploadError={(err) => {
            console.error('Upload error:', err)
          }}
        />
        <p className="text-sm text-[var(--sea-ink-soft)]">
          Uploaded files appear above and in your UploadThing dashboard.
        </p>
      </section>
    </main>
  )
}
