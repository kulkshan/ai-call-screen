# Limitations

- Calls, caller-number behaviour, reports, and labels are generated. They are not customer or production data.
- The offline signal extractor is a reproducible noisy simulator. Gemini is used for live transcript signals, but its per-signal quality has not yet been measured against human labels.
- The live prototype has no real reputation service, STIR/SHAKEN information, or contact graph. It labels those inputs unavailable rather than inventing values.
- The corpus is US-English scripted text. It does not establish performance across languages, accents, regions, or real adversarial behaviour.
- The test split has about 240 calls, so confidence intervals are wide. Dashboard values must be read as synthetic-control results, not real-world performance.
