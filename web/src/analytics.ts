// src/analytics.ts
// Thin wrapper around window.umami — a no-op when the script hasn't loaded
// (ad blockers, tests, offline dev) rather than throwing.
declare global {
  interface Window {
    umami?: { track: (event: string, data?: Record<string, unknown>) => void };
  }
}

export function track(event: string, data?: Record<string, unknown>): void {
  window.umami?.track(event, data);
}
