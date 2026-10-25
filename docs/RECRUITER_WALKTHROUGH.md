# 90-second walkthrough

Public demo: https://kulkshan.github.io/ai-call-screen/

## What to click

1. Choose **Remote access request**.
2. Click **Run Call Screen**.
3. Compare the model action with the expected action.
4. Click **See all 2,000 test results**.

## What to say

**0–15 seconds**

“This project asks one product question: can Call Screen catch scams without blocking legitimate callers?”

**15–35 seconds**

“Here is one simulated call. The classifier scores the transcript, checks whether there is enough evidence to act, and returns BLOCK. The expected label stays hidden until the decision is made.”

**35–55 seconds**

“One correct call is only a demo. I evaluated the same system on a separate final test set: 800 scams, 800 legitimate calls, and 400 intentionally unclear calls.”

**55–75 seconds**

“On the 1,600 calls with a clear label, precision is 93.9%, recall is 98.8%, and the false-positive rate is 6.4%. The confusion matrix shows 790 scams caught, 10 missed, and 51 legitimate calls incorrectly flagged.”

**75–90 seconds**

“The error slices show where I would work next, especially scam warnings and account-information calls. Before rollout, I would repeat the test on human-reviewed real transcripts, run the classifier in shadow mode, and then compare it with a holdout.”

## Honest scope

The benchmark is simulated. The local version has a working Twilio voice flow, but the public recruiter demo is guided so anyone can test it without a phone or microphone.
