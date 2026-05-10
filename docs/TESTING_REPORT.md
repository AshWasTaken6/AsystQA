# AsystQA Website Testing Report

**Date:** May 10, 2026  
**Status:** Passed after fixes  
**Test target:** `http://127.0.0.1:5175` frontend with `http://127.0.0.1:8001` backend  
**Browser path:** Browser plugin was available, but the required Node REPL browser-control tool was not exposed, so testing used Playwright with the local Chrome executable.

## Summary

I ran a full frontend and backend QA sweep covering static checks, production build, API behavior, rendered browser flows, scan generation, report actions, navigation, and mobile layout.

All final checks passed:

- Frontend lint: passed
- Frontend production build: passed
- Backend Python compile check: passed
- Backend `/` health endpoint: passed
- Backend `/analyze` endpoint: passed
- Browser desktop workflow: passed
- Browser mobile smoke/overflow check: passed
- App console health: passed

## Fixes Made During Testing

### 1. Dashboard language state bug

**Problem:** `Dashboard` expected `language` and `setLanguage`, but `App.jsx` did not pass them down. Changing the language selector could break scan controls.

**Fix:** Passed `language` and `setLanguage` from `App.jsx` into `Dashboard`, then into `OverviewDashboard` and `CommandCenterPage`.

**Files:**
- `frontend/src/App.jsx`
- `frontend/src/components/Dashboard.jsx`

### 2. Duplicate stale component code in `App.jsx`

**Problem:** `App.jsx` still contained large duplicate component definitions after the app had been split into component files. This caused lint failures and made behavior harder to trust.

**Fix:** Removed stale duplicate component definitions and kept `App.jsx` focused on app state, auth, scan execution, and report actions.

**File:** `frontend/src/App.jsx`

### 3. React lint and purity issues

**Problem:** Lint failed because of unused React imports, `Date.now()` calls during render, and a synchronous state update inside an effect.

**Fixes:**
- Removed unused `React` default imports.
- Moved scan demo data outside render.
- Replaced render-time `Date.now()` values with deterministic sort keys.
- Reset scan pagination directly in filter/sort change handlers instead of an effect.

**Files:**
- `frontend/src/components/*.jsx`
- `frontend/src/components/OverviewDashboard.jsx`
- `frontend/src/components/ScansPage.jsx`

### 4. False-positive backend issue reporting

**Problem:** Backend agents returned "No security risks detected" and "No major issues found" as report items. The reporter counted those as real issues, and "No security risks detected" was classified as high severity.

**Fix:** Clean/no-action agent results now return zero findings.

**Files:**
- `backend/agents/security.py`
- `backend/agents/reviewer.py`

### 5. Risk level under-reported high severity findings

**Problem:** A scan containing `eval()` and a hardcoded token showed `Risk Level: Low` because risk was based mostly on score.

**Fix:** Reporter risk now respects issue severity. Any high-severity issue produces a high-risk report.

**File:** `backend/agents/reporter.py`

### 6. Local CORS coverage

**Problem:** Backend allowed `localhost` frontend origins but not matching `127.0.0.1` origins, which can break local browser testing depending on the URL used.

**Fix:** Added `127.0.0.1` origins for the local dev ports.

**File:** `backend/core/config.py`

### 7. Browser title and favicon polish

**Problem:** Browser tab title was `frontend`, and the favicon pointed to a missing `/favicon.svg`.

**Fix:** Updated the title to `AsystQA Command Center` and pointed the favicon at `/logo.png`.

**File:** `frontend/index.html`

## What Was Tested

### Static and build checks

| Check | Result | Notes |
|---|---:|---|
| `npm run lint` | Passed | No ESLint errors or warnings after fixes |
| `npm run build` | Passed | Vite production build completed |
| `python -m compileall backend` | Passed | Backend modules compile |
| Backend health endpoint | Passed | `/` returns backend running status |
| Backend analyze endpoint | Passed | `/analyze` returns planner, reviewer, security, tester, reporter, language, timing, and insights |

### Browser desktop flow

| Flow | Result |
|---|---:|
| Intro screen renders | Passed |
| Welcome/landing page renders | Passed |
| Dashboard button opens login modal | Passed |
| Invalid login shows error toast | Passed |
| Demo account autofill works | Passed |
| Valid login opens dashboard | Passed |
| Language selector updates state | Passed |
| Code editor accepts pasted code | Passed |
| Generate QA report calls backend successfully | Passed |
| Security findings render in workflow/results | Passed |
| Issues tab shows findings | Passed |
| Tests tab shows generated test suggestions | Passed |
| Copy report shows confirmation toast | Passed |
| Download report downloads `asystqa-report.txt` | Passed |
| Scans page opens | Passed |
| Scan status filter works | Passed |
| Scan sort control works | Passed |
| Start New Scan opens command page | Passed |
| Reports page shows latest scan result | Passed |
| Settings page opens | Passed |
| Log out returns to landing page | Passed |
| Desktop console errors/warnings | Passed, none found |

### Browser mobile flow

| Flow | Result |
|---|---:|
| Mobile intro page renders at `390x844` | Passed |
| Horizontal overflow check | Passed |
| Mobile console errors/warnings | Passed, none found |

## Evidence Captured

Screenshots were captured outside the repo at:

`%TEMP%\\asystqa-screenshots`

Captured states:

- `01-intro-desktop.png`
- `02-landing-desktop.png`
- `03-dashboard-overview.png`
- `04-scan-results.png`
- `05-intro-mobile.png`
- `qa-results.json`

## Commands Used

```powershell
npm run lint
npm run build
python -m compileall backend
Invoke-WebRequest http://127.0.0.1:8001/
Invoke-RestMethod http://127.0.0.1:8001/analyze
node %TEMP%\\asystqa-e2e-runner.js
```

## Remaining Risks

- Testing was done in local Chrome only, not Firefox/Safari/Edge.
- File upload was code-reviewed but not browser-tested with a real uploaded file.
- History page depends on local backend memory data and was not deeply validated beyond backend health and navigation coverage.
- The Playwright test harness is temporary and not yet committed as a reusable test suite.
