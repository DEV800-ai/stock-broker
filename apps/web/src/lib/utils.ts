import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Backend timestamps are naive UTC ISO strings (no "Z"/offset, e.g. "2026-08-16T14:19:06.387905").
// `new Date(...)` on a string without a timezone marker parses it as local time, not UTC, so
// display would silently be off by the browser's UTC offset. Append "Z" before parsing.
export function formatUtc(iso: string): string {
  const withZone = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  return new Date(withZone).toLocaleString();
}
