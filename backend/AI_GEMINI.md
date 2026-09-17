# FLUX ONE Gemini Academic Copilot

The active Gemini integration now runs inside the FastAPI backend. The old Node.js AI runtime is not required.

## Server environment

Configure these values on the backend deployment only:

```text
GEMINI_API_KEY=<server-side Google AI Studio key>
GEMINI_MODEL=gemini-2.5-flash-lite
```

`GEMINI_MODEL` is optional. The API endpoint and timeout can also be overridden with `GEMINI_API_ENDPOINT` and `GEMINI_TIMEOUT_SECONDS`.

Never put `GEMINI_API_KEY` in `index.html`, Vercel environment variables used by the browser, or any public JavaScript asset.

## Authenticated routes

- `GET /api/v1/ai/status`
- `POST /api/v1/ai/flight-briefing`
- `POST /api/v1/ai/quiz`
- `POST /api/v1/ai/quiz-attempts`

The service verifies that the requested subject belongs to the signed-in student's active enrollments. Prompts contain only subject and verified topic data from PostgreSQL; student names, PRNs, email addresses, passwords, and activity history are not sent to Gemini.

Briefings are cached for 24 hours and generated quiz sets for 7 days. Quiz attempts are graded and saved on the backend.

The frontend loads `assets/ai-fastapi.js`, which adds **AI Briefing** and **AI Quiz** controls to each subject workspace without reviving the legacy Node backend.
