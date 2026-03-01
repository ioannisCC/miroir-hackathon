import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect, useLayoutEffect, useRef } from 'react'
import {
  fetchContacts,
  fetchGuidelines,
  fetchActivePreset,
  fetchPresetList,
  switchPreset,
  updateGuidelines,
  type Contact,
} from '#/lib/api'

function useTextareaHeight(value: string) {
  const ref = useRef<HTMLTextAreaElement>(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])
  return ref
}

export const Route = createFileRoute('/')({
  component: IndexPage,
})

const PRESET_LABELS: Record<string, string> = {
  debt_collection: '💰 Debt Collection',
  recruitment: '🎯 Recruitment',
}

function IndexPage() {
  const qc = useQueryClient()

  // Contacts (auto-filtered by active preset on backend)
  const { data: list, isLoading: contactsLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: fetchContacts,
  })

  // Active preset
  const { data: activePreset } = useQuery({
    queryKey: ['activePreset'],
    queryFn: fetchActivePreset,
  })

  // Available presets
  const { data: presetListData } = useQuery({
    queryKey: ['presetList'],
    queryFn: fetchPresetList,
  })

  // Full guidelines (for settings panel)
  const { data: guidelines } = useQuery({
    queryKey: ['guidelines'],
    queryFn: fetchGuidelines,
  })

  // Switch preset mutation
  const presetMutation = useMutation({
    mutationFn: (name: string) => switchPreset(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['contacts'] })
      qc.invalidateQueries({ queryKey: ['activePreset'] })
      qc.invalidateQueries({ queryKey: ['guidelines'] })
    },
  })

  // Settings state (driven from guidelines)
  const [generalContext, setGeneralContext] = useState('')
  const [callRules, setCallRules] = useState('')
  const [saved, setSaved] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(true)
  const [isLg, setIsLg] = useState(false)

  const contextRef = useTextareaHeight(generalContext)
  const rulesRef = useTextareaHeight(callRules)

  // Sync local state when guidelines load
  useEffect(() => {
    if (guidelines) {
      setGeneralContext(guidelines.general_context || '')
      setCallRules(guidelines.call_rules || '')
    }
  }, [guidelines])

  useEffect(() => {
    const m = window.matchMedia('(min-width: 1024px)')
    const handler = () => setIsLg(m.matches)
    handler()
    m.addEventListener('change', handler)
    return () => m.removeEventListener('change', handler)
  }, [])

  const handleSaveSettings = async () => {
    try {
      await updateGuidelines({ general_context: generalContext, call_rules: callRules })
      qc.invalidateQueries({ queryKey: ['guidelines'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      console.error('Failed to save guidelines:', e)
    }
  }

  const presets = presetListData?.presets ?? []
  const currentPreset = activePreset?.preset_name ?? 'debt_collection'

  return (
    <main className="page-wrap px-4 py-8">
      <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Welcome to MIROIR</h1>
      <p className="mt-2 text-[var(--sea-ink-soft)]">
        Behavioral intelligence for your conversations.
      </p>

      {/* ── PRESET SELECTOR ── */}
      {presets.length > 0 && (
        <div className="mt-6 flex items-center gap-3">
          <label className="text-sm font-medium text-[var(--sea-ink)]">Use case:</label>
          <div className="flex gap-2">
            {presets.map((p) => (
              <button
                key={p}
                type="button"
                disabled={presetMutation.isPending}
                onClick={() => {
                  if (p !== currentPreset) presetMutation.mutate(p)
                }}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  p === currentPreset
                    ? 'bg-[var(--lagoon)] text-white shadow-md'
                    : 'border border-[var(--line)] bg-[var(--surface)] text-[var(--sea-ink)] hover:bg-[var(--chip-bg)]'
                }`}
              >
                {PRESET_LABELS[p] ?? p}
              </button>
            ))}
          </div>
          {presetMutation.isPending && (
            <span className="text-sm text-[var(--sea-ink-soft)] animate-pulse">Switching…</span>
          )}
        </div>
      )}

      {/* Active preset summary */}
      {activePreset && (
        <p className="mt-2 text-xs text-[var(--sea-ink-soft)]">
          Agent role: <span className="font-medium">{activePreset.agent_role}</span> · Context: <span className="font-medium">{activePreset.context_label}</span>
        </p>
      )}

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Settings — left */}
        <details
          open={isLg || settingsOpen}
          onToggle={(e) => setSettingsOpen((e.target as HTMLDetailsElement).open)}
          className="rounded-xl border border-[var(--line)] bg-[var(--surface)] lg:border-0 lg:bg-transparent lg:rounded-none"
        >
          <summary className="cursor-pointer list-none select-none px-4 py-3 text-xl font-semibold text-[var(--sea-ink)] lg:cursor-default lg:py-0 lg:px-0 [&::-webkit-details-marker]:hidden">
            <span className="inline-flex items-center gap-2">
              Guidelines
              {!isLg && (
                <span className="text-sm font-normal text-[var(--sea-ink-soft)]" aria-hidden>
                  {settingsOpen ? '▼' : '▶'}
                </span>
              )}
            </span>
          </summary>
          <div className="border-t border-[var(--line)] px-4 pb-4 pt-4 lg:border-t-0 lg:px-0 lg:pb-0 lg:pt-4">
            <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
              Company guidelines — synced with backend. Changes affect all prompts instantly.
            </p>
            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--sea-ink)]">General context</label>
                <p className="mt-0.5 text-xs text-[var(--sea-ink-soft)]">
                  Who you are, your goals, your tone.
                </p>
                <textarea
                  ref={contextRef}
                  value={generalContext}
                  onChange={(e) => setGeneralContext(e.target.value)}
                  rows={3}
                  className="mt-2 min-h-[4.5rem] w-full resize-none overflow-y-auto rounded-lg border border-[var(--line)]/50 bg-[var(--surface)] p-3 text-sm text-[var(--sea-ink)] placeholder:text-[var(--sea-ink-soft)] focus:border-[var(--lagoon)] focus:outline-none focus:ring-2 focus:ring-[var(--lagoon)]/30"
                  placeholder="Describe your business…"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--sea-ink)]">Call rules</label>
                <p className="mt-0.5 text-xs text-[var(--sea-ink-soft)]">
                  Rules the agent must follow during calls.
                </p>
                <textarea
                  ref={rulesRef}
                  value={callRules}
                  onChange={(e) => setCallRules(e.target.value)}
                  rows={3}
                  className="mt-2 min-h-[4.5rem] w-full resize-none overflow-y-auto rounded-lg border border-[var(--line)]/50 bg-[var(--surface)] p-3 text-sm text-[var(--sea-ink)] placeholder:text-[var(--sea-ink-soft)] focus:border-[var(--lagoon)] focus:outline-none focus:ring-2 focus:ring-[var(--lagoon)]/30"
                  placeholder="Never threaten legal action…"
                />
              </div>
              <button
                type="button"
                onClick={handleSaveSettings}
                className="rounded-lg bg-[var(--lagoon)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
              >
                Save
              </button>
              {saved && <span className="ml-3 text-sm text-[var(--palm)]">Saved ✓</span>}
            </div>
          </div>
        </details>

        {/* Contacts — right */}
        <section>
          <h2 className="text-xl font-semibold text-[var(--sea-ink)]">Contacts</h2>
          <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
            {currentPreset === 'recruitment'
              ? 'Candidates for the active recruitment campaign.'
              : 'Select a contact to view their profile and listen in to a call.'}
          </p>
          {contactsLoading && (
            <p className="mt-4 text-sm text-[var(--sea-ink-soft)] animate-pulse">Loading contacts…</p>
          )}
          {list && list.length > 0 && (
            <ul className="mt-4 space-y-3">
              {list.map((c: Contact) => (
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
                    {c.trust_score != null && (
                      <span className="ml-2 text-sm text-[var(--sea-ink-soft)]">
                        trust {c.trust_score.toFixed(2)}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {list && list.length === 0 && (
            <p className="mt-4 text-sm text-[var(--sea-ink-soft)]">No contacts for this use case.</p>
          )}
        </section>
      </div>
    </main>
  )
}
