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

  "date": "2025-01-30",

  "copper\_eur": 8123.45,

  "aluminium\_eur": 2240.10

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





Remote Price Publishing (Railway API)



In addition to updating Google Sheets, the system can optionally publish the validated metal prices to a remote backend service hosted on Railway.



Purpose



The Railway service acts as a lightweight, authoritative price source for downstream consumers (e.g. client applications, internal tools), providing:



A single current price per metal (no history)



Server-side calculation of ILS price per kg



Centralized access via a simple HTTP API



Google Sheets remains a human-readable reference and operational backup, not a system dependency.



How it works



After prices are successfully:



Scraped from LME



Converted from USD → EUR



Validated against the last known local values



The updater sends the data to the Railway API using a dedicated module:



push\_prices\_to\_railway.py





Each metal is sent independently.



The payload includes:



Metal code (e.g. CU, AL)



Price in EUR per ton



Current EUR → ILS exchange rate



Price date (ISO format)



Example logical flow:



LME (USD/ton)

&nbsp;→ converted to EUR/ton locally

&nbsp;→ validated locally

&nbsp;→ sent to Railway

&nbsp;→ stored as the current authoritative price



API behavior (Railway side)



The backend enforces one row per metal



Incoming data updates the existing row (upsert by metal code)



No historical records are kept



IDs may increment internally (database behavior), but only the latest values are used



The Railway service is designed to be stateless from the updater’s point of view.



Failure handling



If the Railway API call fails:



The failure is logged



A Pushbullet alert is sent



The updater exits with a non-zero status



Local state (last\_prices.json) is only updated after all outputs succeed



This ensures fail-closed behavior and prevents partial or inconsistent updates.



Design notes



The updater performs no reads from Railway



Railway is treated as a write-only publishing target



No retry logic is implemented by design



Any inconsistency must be visible immediately via alerts



This keeps the ingestion path deterministic, debuggable, and aligned with industrial control principles.

