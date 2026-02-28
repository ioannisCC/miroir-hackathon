import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { getMockContacts } from '#/lib/mock'

const STORAGE_KEY = 'miroir_business_settings'

function loadSettings(): { description: string; script_or_edge_cases: string } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as { description?: string; script_or_edge_cases?: string }
      return {
        description: parsed.description ?? '',
        script_or_edge_cases: parsed.script_or_edge_cases ?? '',
      }
    }
  } catch {
    // ignore
  }
  return { description: '', script_or_edge_cases: '' }
}

function saveSettings(description: string, script_or_edge_cases: string) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ description, script_or_edge_cases }))
  } catch {
    // ignore
  }
}

export const Route = createFileRoute('/')({
  component: IndexPage,
})

function IndexPage() {
  const { data: list } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => Promise.resolve(getMockContacts()),
  })

  const [description, setDescription] = useState('')
  const [scriptOrEdgeCases, setScriptOrEdgeCases] = useState('')
  const [saved, setSaved] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [isLg, setIsLg] = useState(false)

  useEffect(() => {
    const loaded = loadSettings()
    setDescription(loaded.description)
    setScriptOrEdgeCases(loaded.script_or_edge_cases)
  }, [])

  useEffect(() => {
    const m = window.matchMedia('(min-width: 1024px)')
    const handler = () => setIsLg(m.matches)
    handler()
    m.addEventListener('change', handler)
    return () => m.removeEventListener('change', handler)
  }, [])

  const handleSaveSettings = () => {
    saveSettings(description, scriptOrEdgeCases)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <main className="page-wrap px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Welcome to MIROIR</h1>
      <p className="mt-2 text-[var(--sea-ink-soft)]">
        Behavioral intelligence for your conversations.
      </p>

      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Settings — left; collapsible on small screens, collapsed by default */}
        <details
          open={isLg || settingsOpen}
          onToggle={(e) => setSettingsOpen((e.target as HTMLDetailsElement).open)}
          className="rounded-xl border border-[var(--line)] bg-[var(--surface)] lg:border-0 lg:bg-transparent lg:rounded-none"
        >
          <summary className="cursor-pointer list-none select-none px-4 py-3 text-xl font-semibold text-[var(--sea-ink)] lg:cursor-default lg:py-0 lg:px-0 [&::-webkit-details-marker]:hidden">
            <span className="inline-flex items-center gap-2">
              Settings
              {!isLg && (
                <span className="text-sm font-normal text-[var(--sea-ink-soft)]" aria-hidden>
                  {settingsOpen ? '▼' : '▶'}
                </span>
              )}
            </span>
          </summary>
          <div className="border-t border-[var(--line)] px-4 pb-4 pt-4 lg:border-t-0 lg:px-0 lg:pb-0 lg:pt-4">
            <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
              Business description and script for edge cases. Stored in this browser only.
            </p>
            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--sea-ink)]">Business description</label>
                <p className="mt-0.5 text-xs text-[var(--sea-ink-soft)]">
                  Purpose of the business, product, tone, goals.
                </p>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  onBlur={handleSaveSettings}
                  rows={3}
                  className="mt-2 w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3 text-sm text-[var(--sea-ink)] placeholder:text-[var(--sea-ink-soft)]"
                  placeholder="Describe your business and product…"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--sea-ink)]">Script / Edge cases</label>
                <p className="mt-0.5 text-xs text-[var(--sea-ink-soft)]">
                  How the agent should handle specific edge cases.
                </p>
                <textarea
                  value={scriptOrEdgeCases}
                  onChange={(e) => setScriptOrEdgeCases(e.target.value)}
                  onBlur={handleSaveSettings}
                  rows={4}
                  className="mt-2 w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] p-3 text-sm text-[var(--sea-ink)] placeholder:text-[var(--sea-ink-soft)]"
                  placeholder="If they ask for a payment plan, offer… If they mention legal action…"
                />
              </div>
              <button
                type="button"
                onClick={handleSaveSettings}
                className="rounded-lg bg-[var(--lagoon)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Save
              </button>
              {saved && <span className="ml-3 text-sm text-[var(--palm)]">Saved.</span>}
            </div>
          </div>
        </details>

        {/* Contacts — right */}
        <section>
          <h2 className="text-xl font-semibold text-[var(--sea-ink)]">Contacts</h2>
          <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
            Select a contact to view their profile and listen in to a call.
          </p>
          {list && list.length > 0 && (
            <ul className="mt-4 space-y-3">
              {list.map((c) => (
                <li key={c.id}>
                  <Link
                    to="/contacts/$contactId"
                    params={{ contactId: c.id }}
                    className="block rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 transition hover:bg-[var(--chip-bg)]"
                  >
                    <span className="font-medium text-[var(--sea-ink)]">{c.name}</span>
                    <span className="ml-2 text-[var(--sea-ink-soft)]">{c.email}</span>
                    {c.risk_score != null && (
                      <span className="ml-2 text-sm text-[var(--sea-ink-soft)]">
                        risk {c.risk_score.toFixed(2)}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {list && list.length === 0 && (
            <p className="mt-4 text-sm text-[var(--sea-ink-soft)]">No contacts in mock data.</p>
          )}
        </section>
      </div>
    </main>
  )
}
