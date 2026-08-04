# 04 — Google integration (Calendar + Tasks)

## What the project syncs to Google

| Need | API used | Result |
|---|---|---|
| Lists (shopping etc.) | **Google Tasks API** | Lists visible in Google Tasks (mobile app, Gmail, Calendar side panel) |
| Meetings | **Google Calendar API** | Events in your calendar, with reminders |
| Text notes | stay on the Pi (web page) | full privacy, no limits |

## Step 1: Project in Google Cloud Console

1. Go to <https://console.cloud.google.com/> and create a new project (e.g. `pi-llm-notetaker`)
2. Under **APIs & Services → Library**, enable:
   - **Google Calendar API**
   - **Google Tasks API**

📚 Tutorial: [Create a Google Cloud project](https://developers.google.com/workspace/guides/create-project)

## Step 2: OAuth consent screen

1. **APIs & Services → OAuth consent screen**
2. Type: **External**, but leave the app in **Testing** mode
3. Add your Gmail address as a **test user**

> Testing mode is 100% sufficient for personal use. The one catch: the refresh token
> expires after 7 days **only if** the app has "Testing" status and sensitive scopes —
> for Calendar/Tasks in testing mode you'll generally need to re-authorize periodically.
> Alternative: publish the app (the "Publish app" button) — for personal use this doesn't
> require Google verification, and tokens stop expiring.

📚 Tutorial: [Configure the OAuth consent screen](https://developers.google.com/workspace/guides/configure-oauth-consent)

## Step 3: Credentials

1. **APIs & Services → Credentials → Create credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Download the JSON file and save it on the Pi as `credentials.json` in the project directory
   (**the file is in `.gitignore` — it never goes into the repo!**)

## Step 4: First authorization (on a headless Pi)

The Pi is headless, so we use the console flow: the `scripts/google_auth.py` script
(created in plan stage 4) prints a URL → you open it **on your computer/phone** →
log in → paste the code back into the Pi's terminal. This produces a `token.json`,
which the app refreshes automatically from then on.

📚 Google's own tutorials (Python quickstart — exactly this mechanism):

- [Google Calendar API — Python quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python)
- [Google Tasks API — Python quickstart](https://developers.google.com/workspace/tasks/quickstart/python)

## Scopes used by the project

```
https://www.googleapis.com/auth/calendar.events   # create/edit events
https://www.googleapis.com/auth/tasks             # lists and tasks
```

Deliberately narrow — the app doesn't have access to, say, reading other people's
entire calendars, or to Gmail.

## What exactly the sync does

- A `meeting` note → `events.insert` on the primary calendar
  (title, date/time from LLM extraction, description = original note text, 30-min popup reminder)
- A `shopping` note → items as tasks on the **"Shopping"** list in Google Tasks
  (the list is created automatically if it doesn't exist)
- A `task` note → a task on the **"PiLLm Note Taker"** list with a due date (`due`)
- Every operation is logged in the `sync_log` table; `external_id` allows updating
  instead of duplicating

Sync is **optional and one-way (Pi → Google)** — enabled via `.env`
(`GOOGLE_SYNC_ENABLED=true`). Two-way sync is a possible future extension (additional stage).

## Checklist

- [ ] Project in Cloud Console with Calendar API and Tasks API enabled
- [ ] Consent screen configured, your email added as a test user
- [ ] `credentials.json` on the Pi (and in `.gitignore`)
- [ ] After plan stage 4: `token.json` generated, a test event visible in the calendar

Next: [05-deployment.md](05-deployment.md)
