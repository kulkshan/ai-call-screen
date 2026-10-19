# Architecture

```mermaid
flowchart LR
  A[Generated labelled calls] --> S[Signal extraction]
  T[Twilio live call] --> S
  S --> M[Computed caller metadata]
  M --> F[Calibrated risk model]
  F --> P[Expected-cost decision]
  P --> R[Evaluation report]
  P --> L[Live call dashboard]
```

The evaluation harness and Twilio adapter use the same signal, fusion, and policy code. The harness supplies generated ground truth and calculated reporter/number history. A live call supplies Gemini transcript signals; a real reputation feed is not present and is marked unavailable.
