import { createFileRoute } from '@tanstack/react-router'
import { createRouteHandler } from 'uploadthing/server'
import { ourFileRouter } from '#/lib/uploadthing-core'

const uploadthingHandler = createRouteHandler({
  router: ourFileRouter,
  config: {
    token: process.env.UPLOADTHING_TOKEN,
  },
})

export const Route = createFileRoute('/api/uploadthing')({
  server: {
    handlers: {
      GET: async ({ request }) => uploadthingHandler(request),
      POST: async ({ request }) => uploadthingHandler(request),
    },
  },
})
