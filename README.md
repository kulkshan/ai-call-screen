# Scam Call Defense Lab

This project evaluates a Call Screen decision pipeline before using it on live calls. A generated, labelled call set feeds the same signal extraction, calibrated risk model, and cost-based action policy used by the Twilio demo. The report currently describes a **synthetic control set**, not real-call performance.

| Synthetic test split | Result | 95% interval |
| --- | ---: | --- |
| Precision | 93.9% | 92.1%–95.4% |
| Recall | 98.8% | 97.7%–99.3% |
| False-positive rate | 6.4% | 4.9%–8.3% |

The separate evidence gate kept 400 of 400 intentionally vague simulated calls in screening, compared with 84 of 400 under the score-only policy. This is a synthetic benchmark result, not a real-world performance claim.

Run `backend\.venv\Scripts\python.exe scripts\run_eval.py` to regenerate the report without network calls. Open the local dashboard at `http://127.0.0.1:3000/lab` after starting the frontend and backend.

See [architecture](docs/ARCHITECTURE.md), [cost model](docs/COST_MODEL.md), [evaluation method](docs/EVAL_METHODOLOGY.md), and [limitations](docs/LIMITATIONS.md).

## Original setup notes

## Start locally (PowerShell)

```powershell
cd C:\Users\shant\ai-call-screen\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
# Copy the example only if .env does not already exist:
if (!(Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env locally and set GEMINI_API_KEY. Never commit it.
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/docs to test POST /analyze with:

```json
{"transcript":"You must pay immediately using gift cards or you will be arrested."}
```

The response contains `risk_level` (low, medium, high, unknown), `reasons` (a list),
and `recommended_action` (continue, verify_independently, hang_up).
GET /health reports server availability, not Gemini connectivity.
Missing keys produce 503, provider/invalid-output errors 502, and timeouts 504.
The default model is gemini-3.8-flash; override it with GEMINI_MODEL if needed.

## Next: connect Twilio

Set PUBLIC_BASE_URL to your public HTTPS origin without a trailing path, and set
TWILIO_AUTH_TOKEN in backend/.env. Expose port 8000 through an HTTPS/WebSocket-capable
tunnel. Configure your Twilio number's incoming-call webhook as:

- POST https://YOUR-PUBLIC-HOST/twilio/voice
- The returned TwiML connects to wss://YOUR-PUBLIC-HOST/twilio/conversation-relay.
- The Connect action callback is POST https://YOUR-PUBLIC-HOST/twilio/complete.

Twilio routes validate X-Twilio-Signature against the configured public origin.
Set TWILIO_PUBLIC_MODE=1 before starting the server for a public tunnel. This disables /analyze, the unauthenticated
local test endpoint. ConversationRelay must be enabled for your Twilio account.

The greeting asks for the caller's name and purpose. The WebSocket accepts setup,
collects prompt segments until last=true, and submits the utterance to Gemini.
It returns an `end` message with a JSON-encoded `handoffData` containing
`{"status":"ok","assessment":{...}}`, or `{"status":"error","error":"..."}`.
Twilio forwards this through its Connect action callback. This milestone's callback
hangs up; it does not store results or route the call. No risk verdict is spoken
to the caller. DTMF/interrupt events are ignored, and disconnects are handled.

No database, frontend, analytics, or call-routing logic is included.
Transcripts and assessments are not persisted by this app; transcript text is sent
to Gemini for assessment. A low rating is not a guarantee that a caller is safe.

## Local glass studio

The frontend is in frontend/index.html, style.css, and app.js. It is served by FastAPI;
no frontend build or Node installation is required.

Run a separate local-only instance while the Twilio tunnel uses port 8000:

```powershell
cd C:\Users\shant\ai-call-screen\backend
$env:TWILIO_PUBLIC_MODE='0'
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001. Choose a scenario, edit the transcript, and click Analyze
conversation for a real Gemini result. The studio shows loading, error, and result
states, supports keyboard navigation and reduced motion, and adapts to narrow screens.
Do not point the public tunnel at port 8001. Keep TWILIO_PUBLIC_MODE=1 on the public
port 8000 instance. Phone-call results are not streamed to this UI yet.
