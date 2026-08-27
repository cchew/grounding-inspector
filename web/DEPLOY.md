# Deploy Checklist

- Analytics uses the self-hosted Umami instance at `umami-indol-one.vercel.app` (not Umami Cloud). `web/index.html` uses `%VITE_UMAMI_WEBSITE_ID%`, substituted by Vite. Production reads it from the `VITE_UMAMI_WEBSITE_ID` Netlify env var (`netlify env:set`); local dev reads it from gitignored `web/.env.local`. This keeps local and production traffic in separate Umami websites.
- Live document-check calls `VITE_API_BASE_URL` (the deployed Modal API). Production reads it from the `VITE_API_BASE_URL` Netlify env var (`netlify env:set VITE_API_BASE_URL https://ching-automation--grounding-inspector-live-api.modal.run`); local dev reads it from gitignored `web/.env.local`.
