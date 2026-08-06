# Deploy Checklist

- Confirm `GATE_SECRET` is set on the Netlify site (Functions scope), 16+ chars. Already done for the current site as of this branch — noted here for future reference/rotation.
- Analytics uses the self-hosted Umami instance at `umami-indol-one.vercel.app` (not Umami Cloud). `web/index.html` uses `%VITE_UMAMI_WEBSITE_ID%`, substituted by Vite. Production reads it from the `VITE_UMAMI_WEBSITE_ID` Netlify env var (`netlify env:set`); local dev reads it from gitignored `web/.env.local`. This keeps local and production traffic in separate Umami websites.
- Run `npm run test:gate:e2e` from a normal (non-worktree) checkout before considering the access gate verified. It could not be run from a git worktree in this branch (confirmed: `netlify dev` resolves `repositoryRoot` to the wrong checkout when run from a linked worktree).
