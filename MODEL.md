# Green House Emission Tracker

This project aims at providing a simple tracker to help companies track their carbon emission. Following the GHG protocols there is a need of more dedicated data models rather than a generic one. The need also lies in area as to reduce the work of the emission coordinator and make the overall process much simpler and effective with minimal effort. This project gives you a simple approach in recording the carbon footprint while making the process simpler but more efficient in its approach.

---

## Core Architecture

The main approach of this project is to handle multi tenancy and source of truth tracking. Hence I have followed the following model.

### The Three Ring Architecture

#### Ring 1 — IngestionBatch

The goal of this ring to ensure the data is not duplicated and also to keep track of what was uploaded at source.

Uses a simple file hash (SHA-256) which acts as a fingerprint of the exact bytecodes uploaded. A duplicate upload is detected before any parsing starts. Therefore a unique key is enforced at the database level.

#### Ring 2 — Raw Activity Row

Stores every origin csv file column-value as a key-value text dictionary, exactly as parsed. It is never over written.

The exact use case of this is the source-of-truth tracking. We will know what was exactly uploaded by the coordinator making it auditable. We would know when and what file was uploaded with time stamps.

A `row_number` records the exact csv line by line (1-indexed) and `parse_status` and `parse_error` records what went wrong at parsing time, separately from what went wrong at normalization.

This is done to ensure a differentiation layer from what the system did wrong and what was wrong in the file uploaded in itself.

#### Ring 3 — Normalized Activity

Stores what the system computed — normalized values, CO2e, flags, review state.

We are able to trace CO2e back to any column and specific cell from csv with exact reasons. We also get what values went in to the calculation which resulted in the corresponding results that we get. This ensure transparency and gives the analyst more time to evaluate the data.

I have also ensure all the reasoning is in simple English so that even non-engineer analyst must be able to understand the calculation and flag it if necessary.

Also has a `is_edited` Boolean ensuring we know who changed what at what stage.

---

A rough diagram of this architecture — the analyst will be able to trace data from Ring 3 back to Ring 2 and Ring 1:

```
IngestionBatch (Ring 1)
    └── RawActivityRow (Ring 2)
            └── NormalizedActivity (Ring 3)
```

---

## Multi-Tenancy

Below is the approach taken to implement Multi-Tenancy.

- Implemented a row-level isolation using a `client` foreign key (FK). Each table that carries business data has a client foreign key (FK). The chain is enforced where every view starts with client check and every queryset filters on it.
- Why row level over schema layer is the simplicity of the approach for a prototype to show how it can be implemented than thinking of other ways it can be implemented, easier audit and simpler for prototype. Set base ViewSet which enforces the filter on every query, so it cannot be forgotten.

A simple visualization of the hierarchy:

```
Client
  └── Submission (client FK)
        └── IngestionBatch (client FK)
              └── RawActivityRow (via batch, no direct FK)
                    └── NormalizedActivity (client FK + batch FK)
  └── ReportingPeriod (client FK)
  └── AuditLog (client FK)
```

- Therefore every API endpoint that returns data filters on client.
- There is no path where tenant A can read tenant B's rows.
- The normalized activity carries both client and batch FK.
- Therefore a User profile is hardly binded to a specific client and a user cannot have access to another user.

---

## Scope 1 / 2 / 3 Categorization

- The Classification happens at parse time and is stored in RawActivityRow — distinguishing it between fuel, electricity, travel_flight, travel_hotel etc.
- Then normalizer (NormalizedActivity) assigns the scope number to it (an integer value 1-2-3) and activity sub type (Diesel, petrol, LPG etc).
- In Scope 3, only category 6 (in GHG protocol category number) is considered in this project (more detail in decisions.md).
- Scope is stored explicitly on every row — it is never computed at query time. This means reporting queries are simple filters, not complex joins.
- Therefore out of scope rows are classified at parse time and excluded from normalization entirely saving time and computation.

---

## Source of Truth Tracking

As mentioned in the architecture, the 3 ring architecture ensure it is easier to track the source of truth for every file, every decision taken.

The following are the kind of source of truth that is tracked at each step:

| Field | What it tracks |
|---|---|
| `source_type` | Which of the three scope is it (SAP / Utility / Travel) |
| `batch` | Which specific file upload is it |
| `raw_row` | Which exact row in the file |
| `raw_quantities` | The original values that was uploaded preserved as text |
| `uploaded_by / uploaded_at` | Who uploaded the file and when |
| `is_edited` | A Boolean flag set when analyst changes a normalized value |

Therefore, we can answer where did this number come from, what did the source say, who processed it and what was never changed.

---

## Unit Normalization

Normalization strategy is as follows:

- Basic three target units — MJ for fuel (Scope 1), kWh for electricity (Scope 2), and km for travel (Scope 3).
- The conversion factors are stored as keys. Material type is the important specificity where a different factor is used for diesel, petrol, LPG etc. The material column makes that distinction.

NormalizedActivity then stores three things:

1. The raw value (`raw_quantity`, `raw_unit`) — what the source said
2. The intermediate value — MJ for Scope 1, kWh for Scope 2, pkm/km/room_night for Scope 3
3. The final value (`co2e_kg`) — the emission estimate

Finally, human readable strings that show the exact arithmetic.

`EmissionFactor` stores `denominator_unit` explicitly. The normalizer multiplies `normalized_quantity` by value only when the units match.

Two step conversion (GAL → L → MJ) makes it robust.

---

## Audit Trail

Every NormalizedActivity row stores the complete history of its existence. The emission factor used is stored as a foreign key — not a copied value — so the exact factor version applied at calculation time is permanently recorded.

When an analyst edits a normalized value, the original value, the new value, the analyst's username, and the timestamp are all appended to the `edit_history` JSON field, and the `is_edited` flag is set to True. The row's status resets to FLAGGED, forcing re-approval — an edit cannot silently pass through.

When an analyst approves a row, `reviewed_by` and `reviewed_at` are stored. When an admin finalizes the reporting period, `locked_at` is set on every row and no further changes are permitted by anyone, including admins.

The original uploaded file is never deleted — IngestionBatch retains the file path and SHA-256 hash of the file as it arrived. The raw values in RawActivityRow are frozen at parse time and never modified.

The result is a complete chain: from the locked CO2e number, back through the analyst's approval, back through the normalization calculation, back through the exact row in the exact file that was uploaded, back to the uploader and timestamp. Every link in that chain is in the database.

---

Therefore this model ensure it a robust system for tracking carbon emission while still enabling future improvements in terms of scope 3 categories (adding new category is just a normalization logic change rather than changing the entire architecture) or cross scope CO2e comparison. Hence it has the ability to handle different shapes, quality and source issue robustly.
