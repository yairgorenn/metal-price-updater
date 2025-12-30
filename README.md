\# Copper \& Aluminium Price Updater



Daily automated system that:

\- Reads official LME copper \& aluminium prices via browser automation

\- Converts USD → EUR using Bank of Israel API

\- Updates Google Sheets

\- Logs all activity

\- Sends Pushbullet alerts on failure



\## Requirements

\- Windows

\- Python 3.12+

\- AutoHotkey

\- Firefox

\- Environment variables:

  - PUSHBULLET\_TOKEN

  - Google credentials (external)



\## Notes

Secrets and runtime files are intentionally excluded from this repository.



\##Price Validation \& Local State (Safety Layer)



To improve robustness and prevent silent data corruption, the system includes a local validation layer based on the last successful run.



Local price cache (last\_prices.json)



After a fully successful update (prices scraped, validated, and written to Google Sheets), the system stores the last known prices locally:



{

&nbsp; "date": "2025-01-30",

&nbsp; "copper\_eur": 8123.45,

&nbsp; "aluminium\_eur": 2240.10

}





This file acts as a local reference point only and is not considered a historical database.



The file is created automatically on the first successful run.



If the file is missing or unreadable, the system treats the run as a first run and continues without comparison.



Validation logic



Before updating Google Sheets, newly fetched prices are validated against the last stored values:



Absolute range check

Prevents obviously invalid values (e.g. parsing errors):



Copper and aluminium must fall within predefined reasonable ranges.



Relative change check

Compares the new price to the last stored price:



Soft limit (≈7%)



Price is accepted



Pushbullet warning is sent



Hard limit (≈20%)



Update is blocked



Pushbullet error is sent



Previous day’s price remains active



Fail-closed behavior



If validation fails, no update is written to Google Sheets.



The local cache is not updated unless the full update succeeds.



Failure scenarios



last\_prices.json missing or deleted



Treated as first run



No validation against previous prices



File recreated after a successful update



Invalid or extreme price detected



Update is aborted



Alert is sent



System exits with non-zero code



Design rationale



This mechanism is intentionally simple and local:



No external dependencies



No historical corrections



No retry logic



The system is designed to stop safely and alert immediately rather than silently propagate incorrect prices.

