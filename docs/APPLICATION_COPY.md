# Application copy

## Portfolio title

**Call Screen Lab — scam detection and model evaluation**

## One-line description

An end-to-end Call Screen prototype that turns a transcript into a scam probability and action, then measures precision, recall, false alarms, missed scams, and unclear-call handling on a held-out simulated test set.

## Resume bullets

- Built an AI Call Screen prototype with Twilio ConversationRelay, FastAPI, Next.js, and a calibrated transcript classifier; evaluated it on 2,000 held-out simulated calls with 93.9% precision and 98.8% recall.
- Designed an evidence-aware decision policy that kept 400 of 400 intentionally unclear simulated calls in screening, up from 84 of 400 with score-only decisions, while exposing subtype false-positive rates and case-level errors.

## LinkedIn or GitHub description

I built Call Screen Lab to show the product data science work behind scam detection, beyond a single AI demo. A guided call shows the model decision. A separate held-out evaluation shows whether the same system catches scams without blocking too many legitimate callers.

The project uses 10,000 simulated, labeled calls: 6,000 for training, 2,000 for calibration, and 2,000 for the final test. The final simulated benchmark reached 93.9% precision and 98.8% recall, with a 6.4% false-positive rate. It also shows the remaining errors and the real-data validation required before rollout.

Stack: Twilio ConversationRelay, FastAPI, Next.js, a calibrated transcript classifier, and GitHub Pages.

Demo: https://kulkshan.github.io/ai-call-screen/

## Interview framing

- **Product problem:** Catch harmful calls without blocking real callers.
- **Modeling:** Convert transcripts into calibrated scam probabilities.
- **Decision policy:** Require enough evidence before allowing or blocking an unclear call.
- **Evaluation:** Measure precision, recall, false-positive rate, confusion matrix, error slices, and unclear-call handling on held-out data.
- **Rollout:** Validate on human-reviewed real transcripts, run in shadow mode, then use a small holdout comparison.

## Claims to avoid

Do not describe the simulated benchmark as real user traffic, Google performance, or a live production experiment.
