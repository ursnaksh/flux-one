# FLUX ONE backend

## Class workspace and activity

The backend seeds a versioned `academic_catalog` from `backend/catalog.mjs`:
seven SY IC-SEDA subjects, 31 weekly timetable slots, six calendar milestones,
four holiday entries and the existing practice library. The seed preserves the
previously imported PDF data; practice topics are labelled as suggestions, not an
official syllabus. Increment the catalog version when deliberately updating it.

Profiles, assignments, notes, study sessions, practice-topic completion, quiz
attempts and activity history are stored per account. The frontend reads these
from the API and confirms saves before updating the interface. Quiz scores are
recomputed on the server; repeated submission of an attempt ID does not duplicate
the result. Active study sessions and their target duration can resume on refresh.

Activity records include successful saved actions and authenticated client click,
view and selection events. Client actions use an allowlist: form values, note
contents, PRNs, passwords, URLs and IP addresses are not copied into activity
records. Click capture can be paused in Activity Log; saved-action history remains.
Each account can read only its own latest events. History retains the latest
5,000 records per account; the UI shows 100. Clicks are batched and retried in
memory while the page remains open, so offline/tab-close delivery is best effort.
Browser interaction records are observations from the client, not proof a save
succeeded; successful saves are separately recorded by the server.

New routes: `GET /api/v1/catalog`, `GET /api/v1/progress`,
`PUT /api/v1/progress/topics`, `POST /api/v1/quizzes/attempts`,
`GET /api/v1/sessions/active`, `GET/POST /api/v1/activity/events`, and
`GET/PUT /api/v1/activity/preferences`. All require authentication.

Classmates' personal roster records still require the owner's CSV/JSON import.
No sample classmates or fabricated academic scores are seeded into production.

The Node.js 24 backend serves both the website and its API. It uses PostgreSQL
when `DATABASE_URL` is set. Local development uses SQLite at
`backend/data/flux-one.db`, or the path provided in `SQLITE_PATH`.

## Local development

From the repository root, run `npm ci` and then `npm start`. Open
http://127.0.0.1:8001/ so the frontend and API share one origin.

Run `npm test` for isolated integration tests. The tests do not use your normal
database and check account isolation and persistence across server restarts.

## Existing Render service

1. Create a Render Postgres database in Oregon, the same region as `flux-one`.
2. Copy its **Internal Database URL** into the web service's **Environment** as
   `DATABASE_URL`. Keep it out of the repository and frontend code.
3. Deploy the backend changes from this repository. The server creates its
   tables on startup and stores its signing key in the database.
4. Open https://flux-one.onrender.com/health and confirm it returns
   `{"status":"ok","database":"PostgreSQL"}`. The health check executes a real
   database query and returns HTTP 503 if the connection is unavailable.
5. Verify registration, login, profile details, notes, and data persistence after
   a service restart before inviting other users.

Render deployments refuse to start without `DATABASE_URL`, so a missing
connection cannot silently switch production back to temporary SQLite storage.
Use the internal connection URL as supplied by Render; the PostgreSQL driver
also accepts TLS settings in a connection URL when a provider requires them.

## Private class roster

After signing in, open **Class Roster**. The first valid import claims the roster
owner account. Import a CSV or JSON `rows` array with `pnr`, `display_name`,
`email`, `roll_number`, and optional `batch` (`B1`, `B2`, or `B3`). Imports are
upserts, so sending the same class again updates changed details. The owner can
see a masked preview; other authenticated students receive only batch totals
and a match for their own profile. PNRs are never included in the aggregate
summary. Only upload records when the students have agreed to this private use.

The `render.yaml` file provides a Blueprint for a new deployment. Adding this
file to an existing manually configured service does **not** automatically
create or attach its database; use the steps above for the existing service.

Render's free database expires after 30 days. It is suitable for an initial
trial; select a paid database plan for continued production use. A free web
service can connect to either database plan. See
https://render.com/docs/free and
https://render.com/docs/postgresql-creating-connecting.

## Existing records

Connecting a new PostgreSQL database does not copy accounts or study data from
SQLite. Existing local SQLite files are left untouched. Do not delete a local
database containing data you need. Records in the previous Render container
can be lost on a redeploy because its filesystem is temporary; arrange an
export/import before switching if any live records need to be retained.
