import { createUploadthing, type FileRouter } from 'uploadthing/server'

const f = createUploadthing()

/**
 * File router for client context uploads (PDF, CSV, Word, etc.).
 * Used by the API route and typed on the client.
 */
export const ourFileRouter = {
  contextFile: f({
    pdf: { maxFileSize: '8MB', maxFileCount: 4 },
    text: { maxFileSize: '4MB', maxFileCount: 4 },
    file: { maxFileSize: '8MB', maxFileCount: 4 },
  }).onUploadComplete(({ file }) => {
    console.log('Context file uploaded:', file.name, file.ufsUrl)
  }),
} satisfies FileRouter

export type OurFileRouter = typeof ourFileRouter
