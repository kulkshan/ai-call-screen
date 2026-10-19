# Browser calling setup

The website uses the Twilio Voice JavaScript SDK. The backend issues a five-minute outgoing-only access token after checking the session bearer token. Twilio calls /twilio/browser-voice; the server verifies its signature and binds the signed client identity to a waiting session. No dialed destination or client-provided session identifier is trusted. The existing ConversationRelay and Gemini flow then handles the call.

In Twilio Console:
1. Copy the Account SID from Account Info.
2. Create a Standard API key in API keys & tokens (US1). Save its SID and secret directly in backend/.env. The secret is shown only once.
3. Create a TwiML App under Voice > Manage > TwiML apps. Set its Voice Request URL to your PUBLIC_BASE_URL followed by /twilio/browser-voice, method POST. Save and copy the Application SID.

Required backend/.env entries:
TWILIO_ACCOUNT_SID=AC...
TWILIO_API_KEY_SID=SK...
TWILIO_API_KEY_SECRET=...
TWILIO_TWIML_APP_SID=AP...

The existing TWILIO_AUTH_TOKEN and PUBLIC_BASE_URL are also required. Never place API secrets in NEXT_PUBLIC variables or commit .env. Restart FastAPI and refresh the website after configuration. Changing the temporary tunnel requires updating both the TwiML App webhook and PUBLIC_BASE_URL; keep the phone-number webhook at /twilio/voice.

Local start, in backend:
$env:TWILIO_PUBLIC_MODE='1'
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8002 --no-access-log

In web: npm run dev

Open http://127.0.0.1:3000 in a browser with microphone support. Consent, click Talk to the screening agent, allow microphone, and speak fictional details. Mute and End call control browser audio. Refreshing or leaving ends browser audio. A completed decision remains in the session until expiry. On deployed sites, HTTPS is required.

Verification completed: backend tests cover private token access, short expiry, outgoing-only grants, signature validation, one-call ownership, browser-to-ConversationRelay routing, and a mocked classification. Frontend production build passed. Actual microphone-to-Twilio audio remains unverified until the required account settings are supplied.

Operational limits: this remains a single-host demonstration with local SQLite and process-local rate limits. It is not ready for unrestricted public traffic or multiple Cloud Run instances. Browser calls incur Twilio and Gemini usage. A recorded-example fallback has not been added because no suitable completed recording has been captured.
