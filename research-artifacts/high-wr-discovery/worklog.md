# HydraAI high-WR discovery worklog

- Latest screen: 2026-11-15T08:26:20.572738+00:00
- Branch: hydra/research-validation
- Candidate batch eligibility: 5/5; batch_ready=True
- Dedupe check: no exact match found in the existing prior-period sweep/reclaim, indicator, abnormal-impulse or three-candidate forward definitions. Three fix-window variants are related by one published mechanism and are not independent evidence.

## HYD-NEW-001 — Tokyo fix post-reversal

- Fixed rules: {"id": "HYD-NEW-001", "name": "Tokyo fix post-reversal", "family": "FX fixing reversal", "zone": "Asia/Tokyo", "fix": "09:55", "side_rule": "fade the EURUSD return over the 60 minutes ending at the fix", "expiry_min": 15}
- Validation N=135; W/L/D=65/69/1; WR=48.507%; net@92=-9.20u; status=SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET.
- New prospective N since 2026-11-15: 0.

## HYD-NEW-002 — ECB fix post-reversal

- Fixed rules: {"id": "HYD-NEW-002", "name": "ECB fix post-reversal", "family": "FX fixing reversal", "zone": "Europe/Berlin", "fix": "14:15", "side_rule": "fade the EURUSD return over the 60 minutes ending at the fix", "expiry_min": 15}
- Validation N=147; W/L/D=74/72/1; WR=50.685%; net@92=-3.92u; status=SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET.
- New prospective N since 2026-11-15: 0.

## HYD-NEW-003 — London fix post-reversal

- Fixed rules: {"id": "HYD-NEW-003", "name": "London fix post-reversal", "family": "FX fixing reversal", "zone": "Europe/London", "fix": "16:00", "side_rule": "fade the EURUSD return over the 60 minutes ending at the fix", "expiry_min": 15}
- Validation N=148; W/L/D=74/72/2; WR=50.685%; net@92=-3.92u; status=SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET.
- New prospective N since 2026-11-15: 0.

## HYD-NEW-004 — London opening-hour drift

- Fixed rules: {"id": "HYD-NEW-004", "name": "London opening-hour drift", "family": "Local-session seasonality", "zone": "Europe/London", "fix": "08:00", "side_rule": "fixed CALL at the first M5 open at 08:00 London time", "expiry_min": 30}
- Validation N=146; W/L/D=65/80/1; WR=44.828%; net@92=-20.20u; status=SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET.
- New prospective N since 2026-11-15: 0.

## HYD-NEW-005 — M5 volatility-squeeze breakout

- Fixed rules: {"id": "HYD-NEW-005", "name": "M5 volatility-squeeze breakout", "family": "Volatility compression/expansion", "zone": "UTC", "fix": null, "side_rule": "breakout direction after a 12-bar range falls in the bottom 20% of the preceding 96 rolling 12-bar ranges", "expiry_min": 15}
- Validation N=573; W/L/D=278/290/5; WR=48.944%; net@92=-34.24u; status=SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET.
- New prospective N since 2026-11-15: 0.
