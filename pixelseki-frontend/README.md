# PixelSeki — Frontend

Vue 3 frontend for PixelSeki. Pixel-art themed UI for generating game assets with AI.

## Prerequisites

- Node.js 20.19+ or 22.12+
- npm
- Backend API running on `http://localhost:8000`

## Setup

```bash
npm install
```

## Environment Variables

Create `.env` in this directory:

```env
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=198...apps.googleusercontent.com
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API base URL |
| `VITE_GOOGLE_CLIENT_ID` | Yes | — | Google OAuth Client ID. Must match `GOOGLE_CLIENT_ID` in the backend `.env` |

## Running

```bash
npm run dev
```

Opens at `http://localhost:5173` with hot-reload.

### Other Commands

```bash
# Production build (type-checks with vue-tsc, then builds with Vite)
npm run build

# Preview production build
npm run preview

# Type check
npm run type-check

# Run tests
npm run test:unit

# Lint (oxlint + eslint with auto-fix)
npm run lint

# Format (prettier)
npm run format
```

## Project Structure

```
src/
├── main.ts                          # App entry — Pinia, Router, mount
├── App.vue                          # Root component (RouterView)
├── style.css                        # Global styles, fonts, retro effects
│
├── router/
│   └── index.ts                     # 5 routes (see below)
│
├── lib/
│   └── api.ts                       # apiFetch() — JWT auth, FormData support
│
├── stores/
│   ├── auth.ts                      # Google OAuth, JWT persistence, user state
│   ├── generations.ts               # Jobs CRUD, SSE streaming, item management
│   └── creations.ts                 # Creations CRUD, polling, version management
│
├── views/
│   ├── HomeView.vue                 # Landing page — hero, features, showcase
│   ├── ObjectsView.vue              # Sprite Generator — asset grid + create modal
│   ├── AssetDetailView.vue          # Asset detail — per-direction edit/redo/download
│   ├── CreationView.vue             # Creation Studio — form + history list
│   └── CreationDetailView.vue       # Creation detail — magnifier, versions
│
└── components/
    └── AppNavbar.vue                # Responsive navbar with auth state

public/
├── assets/
│   ├── bg-dark.jpg                  # Dark mode hero background
│   └── bg-ligth.jpg                 # Light mode hero background
└── showcase/                        # Landing page showcase images
```

## Pages

| Route | View | Description |
|---|---|---|
| `/` | HomeView | Landing page with feature showcase and login |
| `/objects` | ObjectsView | List all generation jobs + create new sprites/tilesets |
| `/objects/:id` | AssetDetailView | Manage directions/tiles — edit, redo, add, download |
| `/creation` | CreationView | Single-image generation with category/direction/size options |
| `/creation/:id` | CreationDetailView | Preview with magnifying glass, version history |

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Vue 3 | ^3.5 | UI framework (Composition API, `<script setup>`) |
| TypeScript | ~6.0 | Type safety |
| Pinia | ^3.0 | State management |
| Vue Router | ^4.6 | Client-side routing with lazy loading |
| Tailwind CSS | ^3.4 | Utility-first styling |
| Vite | ^8.0 | Dev server + build tool |

## Key Implementation Details

### API Client (`lib/api.ts`)

All API calls go through `apiFetch()`:
- Reads JWT from `localStorage` and adds `Authorization: Bearer` header
- Sets `Content-Type: application/json` by default
- Auto-skips `Content-Type` for `FormData` bodies (lets browser set multipart boundary)
- Throws `Error` with server's `detail` message on non-2xx responses

### Auth Flow

1. Google Identity Services SDK loaded in `index.html`
2. User clicks Sign In → GIS returns `id_token`
3. Token sent to `POST /api/v1/auth/google/login`
4. Backend returns JWT → stored in `localStorage`
5. All subsequent API calls include the JWT

### SSE Streaming (Generations)

`EventSource` doesn't support custom headers. The workaround:
- Uses `fetch()` with `Authorization` header
- Reads the response as a `ReadableStream`
- Parses SSE `data:` lines manually
- Updates store reactively as each sprite direction completes

### Polling (Creations)

Simpler than SSE — polls `GET /api/v1/creations/{id}` every 2 seconds until status is `completed` or `failed`.

## Styling

- Custom game-themed Tailwind palette (`game-dark`, `game-accent`, `game-sakura`, `game-gold`)
- Pixel font: Press Start 2P
- Terminal font: VT323
- Body font: Outfit
- Mono font: JetBrains Mono
- Retro effects: scanlines, CRT overlay, glow text shadows, checkerboard transparency preview

### Configuration Files

- [vite.config.ts](vite.config.ts) — Vite configuration
- [tailwind.config.js](tailwind.config.js) — Tailwind theme (custom colors, fonts, shadows)
- [tsconfig.json](tsconfig.json) — TypeScript configuration

## Troubleshooting

| Problem | Solution |
|---|---|
| Google Sign-In button missing | Check `VITE_GOOGLE_CLIENT_ID` in `.env` |
| API calls fail with CORS | Backend must be on port 8000, frontend on 5173 |
| "API error 401" | JWT expired — sign out and sign in again |
| Images not loading | Check backend is running and serving static files at `/static/` |
| Build fails type check | Run `npm run type-check` to see TypeScript errors |
