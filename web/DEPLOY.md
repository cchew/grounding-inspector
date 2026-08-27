# Deploy Checklist

- Analytics uses the self-hosted Umami instance at `umami-indol-one.vercel.app` (not Umami Cloud). `web/index.html` uses `%VITE_UMAMI_WEBSITE_ID%`, substituted by Vite. Production reads it from the `VITE_UMAMI_WEBSITE_ID` Netlify env var (`netlify env:set`); local dev reads it from gitignored `web/.env.local`. This keeps local and production traffic in separate Umami websites.
- Live document-check calls `VITE_API_BASE_URL` (the deployed Modal API), committed in `web/.env.production` — Vite loads it automatically for production builds. Local dev reads it from gitignored `web/.env.local`.
