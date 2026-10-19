# Stable public deployment

The local stack is only for development. A recruiter-facing demo uses:

- Cloud Run for FastAPI and ConversationRelay WebSockets.
- Firestore in Native mode for short-lived private sessions.
- Vercel for Next.js, configured with the Cloud Run URL.

## Cloud project setup

In project `ai-call-screen`, enable Cloud Run, Cloud Build, Artifact Registry, Firestore, and Secret Manager APIs. Create Firestore in Native mode in the chosen region. Give the Cloud Run runtime service account `Cloud Datastore User` so it can read and update only Firestore session documents.

Store these as Cloud Run secrets: `GEMINI_API_KEY`, `TWILIO_AUTH_TOKEN`, `TWILIO_API_KEY_SECRET`. Store the non-secret Twilio SIDs and `SESSION_STORE=firestore` as environment variables. The container does not need a local `.env` file.

Deploy this repository with the `Dockerfile`, setting `--port 8080`, request-based billing, `--min-instances 0`, and a maximum of one instance for this private portfolio demo. This avoids an always-on server charge and caps concurrent traffic. Once Cloud Run returns its HTTPS URL, set:

- `PUBLIC_BASE_URL` to that URL.
- `FRONTEND_ORIGINS` to the Vercel production URL.
- Twilio phone-number Voice URL to `PUBLIC_BASE_URL/twilio/voice` (POST).
- Twilio Browser TwiML App Voice URL to `PUBLIC_BASE_URL/twilio/browser-voice` (POST).

Then set Vercel `NEXT_PUBLIC_API_URL` to `PUBLIC_BASE_URL` and redeploy the `web/` directory.

## Verification before sharing

1. `GET /health` returns 200 from the Cloud Run URL.
2. Browser microphone test shows transcript and final decision.
3. A browser refresh can still retrieve an unexpired session.
4. Phone fallback reaches the same backend.
5. Confirm no `.env`, session database, or evaluation result contains credentials or real caller data.

Cloud Run is stable but billable. The quick Cloudflare URL is no longer part of the public deployment.
