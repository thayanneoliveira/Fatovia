# FatoVia Watchdog (Cloudflare Workers Free)

Independent supervisor, isolated from the Instagram token. Scope: the currently approved documentary pilot, 15–21 November 2026; Brazil UTC-3. The current GitHub publisher remains the authority, including its source, media, quota and duplicate guards.

## Deploy
Cloudflare Workers & Pages > create Worker via GitHub. Select only this repository. Worker name `fatovia-watchdog`, branch `main`, root directory `watchdog`, deploy command `npx wrangler deploy`. No custom domain or paid product. Cron every five minutes from wrangler.jsonc. No public route.

Runtime secrets via Worker Settings, Variables and Secrets (not Build secrets): `GITHUB_TOKEN`, a fine-grained GitHub PAT restricted to this repository, Actions Read/write, Contents Read, Variables Read, Metadata Read. Use expiry, rotate/revoke when needed. Actions write is repo-wide, not restricted to publish.yml by the token; the code only calls dispatch of publish.yml on main. Never commit the token or send it in a message. The Cloudflare GitHub build integration has separate permissions; limit repo scope.

Default observe-only. `WATCHDOG_MODE` must explicitly be set to `active` after observing logs and passing integration tests. Keep GitHub schedule and ChatGPT email monitor unchanged. For kill switch remove WATCHDOG_MODE or set observe. Revoking token disables all authenticated checks. The Python publish gate remains independent.

## Behavior
Check gate, policy and state at a pinned branch SHA, recent workflow runs, date/slot, quota, duplicate, gap and pending eligibility. Give the primary schedule a grace period; avoid in-flight jobs, limit dispatch attempts; never retry a failed run automatically or touch uncertain transactions. Use workflow_dispatch only. No arbitrary public request triggers. On failure log sanitized reason. Log delivery is not email; existing email monitor is separate. GitHub concurrence and Meta reconciliation remain mandatory. Checks are best effort, not exactly-once dispatch; lack of atomic external lock is a residual race. Cron and API limits, 10ms free CPU, token expiry and whole-GitHub outage need real validation. No automatic extension after pilot.

## Tests
`node --test watchdog/test.mjs` from repository root. The test cases check decision logic only, not deployed runtime or live API. 

### Deployment from repository root (mobile-friendly)
A matching root `wrangler.jsonc` is provided, pointing only at `watchdog/src/index.mjs`. When Cloudflare root directory is blank or `/`, use `npx wrangler deploy` with no custom build command. If using root directory `watchdog`, the nested config still works. Both configurations must keep equivalent triggers, no public routes and observe-only default. Do not merge Cloudflare-generated auto-configuration blindly. Check the deployment log for the expected Worker and verify cron before adding runtime secrets.

## Diagnostic revision v2
The initial real cron invocation emitted `supervision_failed`, without a usable cause. Version `watchdog-diagnostic-v2` emits a controlled stage and reason, never raw API response or exception. In observation mode, every cron can test authenticated GETs even outside publication windows; successful snapshots emit `github_read: ok`. Active mode still skips outside candidate hours and requires explicit activation. A 20-run page is rejected if it may omit runs from the last day. Local tests use mocked transport, not a live token. The real deployment log is required before activation. Publication gap aligned with the existing Python executor (3 hours); its other guards remain authoritative.
