# Sample data

`sample_events.csv` is a small **synthetic** dataset (no personal data or credentials).

| Column | Meaning |
|---|---|
| `event_id` | Event identity (`TYPE:identifier`). **This column alone decides duplicate status.** |
| `event_type` | Category, repeated from the ID prefix for readability |
| `timestamp` | ISO 8601 time, 7 minutes apart; not used for matching |

Contents: 60 rows, 34 distinct `event_id` values, 26 repeated occurrences, five event types
(`USER_LOGIN`, `PAYMENT`, `FILE_UPLOAD`, `SENSOR_ALERT`, `PAGE_VIEW`); the most repeated IDs appear four times.

Encoding: UTF-8, comma separated, header row required.
