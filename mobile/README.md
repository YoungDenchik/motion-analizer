# AI Fitness Coach — Mobile App

React Native + Expo mobile client for the AI Fitness Coach backend.  
Works on iPhone via **Expo Go** during development — no Mac, no Xcode required.

---

## Prerequisites

| Tool | Version |
|---|---|
| Node.js | 18+ |
| npm | 9+ |
| Expo Go (iPhone) | Latest from App Store |

---

## Setup

### 1. Install dependencies

```bash
cd mobile
npm install
```

### 2. Find your computer's local IP

Open PowerShell and run:
```
ipconfig
```
Look for **IPv4 Address** under your Wi-Fi adapter (e.g. `192.168.1.105`).  
Your iPhone and computer must be on the **same Wi-Fi network**.

### 3. Start the backend

From the repo root (activate the venv first):
```bash
.venv\Scripts\activate
# Either run directly:
python api.py
# Or via Docker Compose:
docker-compose up
```

### 4. Start the Expo dev server

```bash
cd mobile
npx expo start
```

A QR code appears in the terminal.

### 5. Open on iPhone

1. Open **Expo Go** on your iPhone
2. Tap **Scan QR Code** and scan the code from the terminal
3. On the Setup screen enter your server URL, e.g. `http://192.168.1.105:8000`
4. Enter your name and tap **Connect**

> **Port note:** If running the backend directly with `python api.py`, use port `8000`.  
> If running via Docker + Nginx, use port `80` (the default).

---

## Project Structure

```
mobile/
├── App.tsx                        # Root component
├── app.json                       # Expo config
├── package.json
├── tsconfig.json
└── src/
    ├── api/
    │   ├── client.ts              # Axios instances with interceptors
    │   └── endpoints.ts           # Typed API functions
    ├── components/
    │   ├── common/                # Button, Card, LoadingSpinner, ErrorMessage, StatusBadge
    │   └── exercise/              # ScoreDisplay, FeedbackCard, RepScoreList, ErrorEventList
    ├── constants/
    │   └── index.ts               # Colors, spacing, typography, polling config
    ├── hooks/
    │   ├── useAnalysis.ts         # Upload + job-start lifecycle
    │   ├── useExercises.ts        # Fetch / delete exercise references
    │   └── useJobPoller.ts        # Long-polls /api/status/{job_id}
    ├── navigation/
    │   ├── AuthNavigator.tsx      # Stack: Setup
    │   ├── MainNavigator.tsx      # Bottom tabs + nested stacks
    │   └── RootNavigator.tsx      # Auth gate, reads Zustand store
    ├── screens/
    │   ├── auth/SetupScreen.tsx          # Server URL + name → connectivity test
    │   ├── home/HomeScreen.tsx           # Dashboard with quick actions
    │   ├── exercises/
    │   │   ├── ExercisesScreen.tsx       # List + pull-to-refresh + delete
    │   │   └── RecordReferenceScreen.tsx # Upload reference video
    │   ├── analyze/
    │   │   ├── AnalyzeScreen.tsx         # Select exercise + pick video
    │   │   ├── JobPollingScreen.tsx      # Processing indicator
    │   │   └── ResultScreen.tsx          # Score, video, feedback, stats
    │   └── settings/SettingsScreen.tsx   # Edit URL/name, disconnect
    ├── services/
    │   └── storage.ts             # AsyncStorage wrapper (typed keys)
    ├── store/
    │   └── authStore.ts           # Zustand: auth state + AsyncStorage sync
    └── types/
        ├── api.ts                 # All API response/request interfaces
        └── navigation.ts          # React Navigation param list types
```

---

## Screens

| Screen | Description |
|---|---|
| **Setup** | Enter server URL, test connectivity, save profile |
| **Home** | Dashboard: exercise count, quick-action cards |
| **Exercises** | List references (pull to refresh), swipe-delete, navigate to Record |
| **Record Reference** | Pick video, name exercise, upload to backend |
| **Analyze** | Select exercise pill, pick user video, start analysis |
| **Job Polling** | Live progress messages while backend processes the video |
| **Result** | 3-tab view: Overview (score + reps), Feedback (cues), Details (stats + error events) + annotated video player |
| **Settings** | Edit server URL / name, disconnect |

---

## Extending

- **Add a new screen:** Create the screen in `src/screens/`, register it in the relevant navigator in `MainNavigator.tsx`, and add its params to `src/types/navigation.ts`.
- **Add a new API call:** Add a typed function to `src/api/endpoints.ts`. The Axios client + base URL injection are already wired.
- **Add global state:** Create a new Zustand store in `src/store/`. No providers needed.
- **Style changes:** All design tokens live in `src/constants/index.ts` (colors, spacing, typography).
