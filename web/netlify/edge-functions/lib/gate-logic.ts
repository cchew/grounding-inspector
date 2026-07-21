// netlify/edge-functions/lib/gate-logic.ts
// Pure logic for the access gate — no Netlify/Deno runtime dependency, so this
// is testable with plain Vitest. gate.ts (the actual edge function) wires this
// into Request/Response and the Netlify Context.
//
// Lives in lib/, not directly in edge-functions/, because Netlify's bundler
// auto-registers every top-level file in edge-functions/ as its own function
// and fails on this one (no default export) — nested files are shared code,
// not auto-discovered.

const ALLOWED_EMAILS = ["test.user@gmail.com", "test.user@example.org"];

export function isAllowedEmail(email: string): boolean {
  return ALLOWED_EMAILS.includes(email.trim().toLowerCase());
}

export const COOKIE_NAME = "gi_gate";
export const COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days, seconds

const COOKIE_VALUE = "1";

async function hmac(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

export async function signCookieValue(secret: string): Promise<string> {
  const sig = await hmac(secret, COOKIE_VALUE);
  return `${COOKIE_VALUE}.${sig}`;
}

export async function verifyCookieValue(secret: string, cookieHeader: string | null): Promise<boolean> {
  if (!cookieHeader) return false;
  const match = cookieHeader.match(new RegExp(`(?:^|;\\s*)${COOKIE_NAME}=([^;]+)`));
  if (!match) return false;
  const raw = decodeURIComponent(match[1]);
  const [value, sig] = raw.split(".");
  if (value !== COOKIE_VALUE || !sig) return false;
  const expected = await hmac(secret, COOKIE_VALUE);
  return sig === expected;
}

export function gateFormHtml(rejected = false): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Grounding Inspector</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 420px; margin: 20vh auto; padding: 0 1.5rem; color: #1a1a1a; }
  h1 { font-size: 1rem; }
  p { font-size: 0.875rem; color: #444; }
  input { width: 100%; padding: 0.5rem; margin: 0.5rem 0; box-sizing: border-box; }
  button { padding: 0.5rem 1rem; }
  .rejected { color: #a02020; }
</style>
</head>
<body>
  <h1>Grounding Inspector</h1>
  <p>Enter the email of the person who told you about this tool.</p>
  ${rejected ? '<p class="rejected">Access is limited right now.</p>' : ""}
  <form method="POST">
    <input type="email" name="email" required autofocus />
    <button type="submit">Continue</button>
  </form>
</body>
</html>`;
}
