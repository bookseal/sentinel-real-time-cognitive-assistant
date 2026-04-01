# 2026-04-01 12:45 — Persistent Alert Banner (10 seconds)

## What was done

- Added 10-second persistent alert banner to the volume gauge UI
- When volume exceeds WARNING_DB (60 dB) or ALERT_DB (70 dB), a colored banner appears and stays for 10 seconds
- Red alert stays red even if a yellow-level sound follows (doesn't downgrade mid-alert)
- Timer resets on each new loud chunk (continuous shouting = continuous alert)
- Fixed Dockerfile inline comment syntax error (ENV lines)

## Why

The previous gauge updated every 500ms — alerts disappeared instantly. Users need at least 10 seconds to notice the warning and lower their voice.

## Files changed

| File | Change |
|------|--------|
| `app.py` | Added `time` import, `alert_state` global, alert logic in `process_audio`, banner in `generate_gauge_html` |
| `Dockerfile` | Moved inline comments above ENV lines (Dockerfile syntax doesn't allow inline `#` on ENV) |

## Verification commands

```bash
# 1. Pod running
kubectl get pods -l app=sentinel

# 2. Check logs
kubectl logs deployment/sentinel --tail=5

# 3. Browser test
# Open https://sentinel.bit-habit.com → record → speak loudly → banner should appear for 10s

# 4. Check alert_state exists in code
grep -n "alert_state" app.py
```
