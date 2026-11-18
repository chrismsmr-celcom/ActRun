# Cerbere Cohort dashboard

Frontend preview for the Cerbere Cohort coordination runtime.

## Stack
- React + TypeScript
- Vite
- Lucide icons
- CSS design tokens with dark and light themes

## Run locally
```powershell
cd web
npm install
npm run dev
```

## Current state
This is an interface-first preview. Dashboard values are sample data and are explicitly labelled. Navigation, theme switching, search input, preview notifications and the create-task preview are client-side only. No runtime API calls or persistence are wired yet.

## Next integration steps
1. Connect workspace/runtime health.
2. Replace sample agent and event data with MCP/API responses.
3. Wire agent, task, shared-state and lease views.
4. Add conflict inspection and resolution actions.
5. Add workspace settings and persistent theme preference.
