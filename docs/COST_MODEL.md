# Cost model

The policy chooses the action with the lowest expected cost for the model’s calibrated scam probability.

| Action | Cost if scam | Cost if legitimate |
| --- | ---: | ---: |
| Allow | 1.00 | 0.00 |
| Keep screening | 0.50 | 0.02 |
| Warn | 0.33 | 10.00 |
| Block | 0.00 | 50.00 |

Blocking a genuine caller is set as much more costly than missing a scam because it is a silent product failure. Continuing to screen has a small cost because extra delay is also a user harm. The Threshold Lab changes the false-positive cost and recalculates the action boundaries; it does not move a hidden hand-picked threshold.
