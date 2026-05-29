# Tradeoffs

This document contains the 3 main Tradeoffs that I chose to make.

---

## 1. Hardcoded Material Codes Instead of Per-Client Config

The current MaterialGroupLookup is a static fixture seeded at deployment time with codes designed to match the sample. It is not configurable per client through the application.

- Adding a new client's material codes requires database migration or a Django admin edit.
- What production requires: a per client material mapping interface where, during onboarding, the client updates their SAP material master extract and maps each material code to a fuel type.
- The lookup architecture was deliberately chosen over keyboard matching because per client configuration is the correct long term design. This is only for prototype and not a constraint.

---

## 2. CSV Upload Instead of Live API Integration for Travel Data

- The Concur API (developer.concur.com) exposes expense entries through an OAuth 2.0 authenticated REST endpoint. A production integration would authenticate using a corporate-level OAuth token, poll the expense reports endpoint nightly.

Three specific reasons this was not built:

**First, OAuth credentials.** Concur API access requires the client's IT team to register an application in their Concur tenant and issue a client ID and secret. This is not a self-service process — it requires a Concur administrator and often a vendor security review. It is a weeks-long process that cannot happen during a prototype sprint.

**Second, the custom field problem.** Origin and destination airport codes in Concur are stored in custom fields (Custom1, Custom2 etc.) configured differently per company. An API integration that works for one client's Concur setup will return empty airport fields for another client whose admin put the codes in Custom7 and Custom8. Each client requires its own field mapping configuration before the API integration produces usable data.

**Third, Navan's API is significantly less documented than Concur's.** The most complete documentation available is Fivetran's connector documentation, which is a third-party source. Building a reliable integration against an underdocumented API in a prototype sprint is high risk.

- CSV export sidesteps all three problems. The sustainability team gets a CSV from finance, uploads it, and the system processes it. The same data arrives, just through a human instead of an automated pull.

---

## 3. PDF Utility Bill Parsing

- PDF utility bills are the most common format in which Indian utility providers deliver billing data to commercial customers.
- PDF parsing was excluded because the engineering cost is not up to what it unlocks for a prototype. Two distinct problems make it genuinely difficult.

**First, every utility produces a different PDF layout.** BESCOM's bill places consumption in the bottom-left table. MSEDCL's bill uses a different structure entirely. A parser written for BESCOM's layout produces garbage output for MSEDCL's.

**Second, many older utility bills are scanned images embedded in a PDF envelope.** These require OCR before any extraction can happen. OCR on utility bills which contain tables, rotated text, stamps, and low-resolution scans has a meaningful error rate. An incorrect kWh value that passes through OCR without detection would produce a wrong CO2e calculation that neither the system nor the analyst can easily catch.
