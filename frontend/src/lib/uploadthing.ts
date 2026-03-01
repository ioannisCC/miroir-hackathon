import {
  generateUploadButton,
  generateUploadDropzone,
} from '@uploadthing/react'
import type { OurFileRouter } from './uploadthing-core'

/**
 * Typed UploadThing components. Use url when the app is not at the same origin as the API
 * (e.g. in production with a different domain). For same-origin dev, "/api/uploadthing" works.
 */
const getUploadthingUrl = () => {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/uploadthing`
  }
  return '/api/uploadthing'
}

export const UploadButton = generateUploadButton<OurFileRouter>({
  url: getUploadthingUrl(),
})

export const UploadDropzone = generateUploadDropzone<OurFileRouter>({
  url: getUploadthingUrl(),
})
