import type { ClassValue } from 'clsx'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Pretty-print JSON with 2-space indent for readable display. */
export function prettyPrintJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}
