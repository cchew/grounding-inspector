# Deploy Checklist

- Confirm `GATE_SECRET` is set on the Netlify site (Functions scope), 16+ chars. Already done for the current site as of this branch — noted here for future reference/rotation.
- Replace `data-website-id="REPLACE_WITH_REAL_UMAMI_WEBSITE_ID"` in `web/index.html` with a real Umami Cloud website ID (create the account/site first).
- Run `npm run test:gate:e2e` from a normal (non-worktree) checkout before considering the access gate verified. It could not be run from a git worktree in this branch (confirmed: `netlify dev` resolves `repositoryRoot` to the wrong checkout when run from a linked worktree).
