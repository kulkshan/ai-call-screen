# Evaluation methodology

The corpus contains 1,200 generated scenarios: 600 scam and 600 legitimate. Scam calls include 450 standard cases and 150 adversarial paraphrases. Legitimate calls include 450 ordinary cases and 150 legitimate calls designed to resemble scams.

Scenario groups are split 60/20/20 into train, validation, and test. An adversarial rewrite stays with its parent scenario. Reporter profiles are also assigned to a single split, so test-time reputation features are not based on reporters seen during model training.

The train split fits logistic fusion; validation fits isotonic calibration; the test split is used once for the report. The report shows precision, recall, false-positive and false-negative rates with Wilson 95% intervals, AUC-PR, calibration error, per-signal quality, and per-archetype results. AUC-PR is included because class imbalance makes ROC look better than the operational trade-off.
