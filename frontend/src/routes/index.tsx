import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: IndexPage })

function IndexPage() {
  return (
    <main className="page-wrap px-4 py-8">
      <h1 className="text-2xl font-bold text-(--sea-ink)">
        Welcome
      </h1>
      <p className="mt-4 text-(--sea-ink-soft)">
        This is the home page.
      </p>
    </main>
  )
}
