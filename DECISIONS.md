# Decisions

This document covers all the key decisions taken during the project.

---

## 1. DB Design

Important decision here is why 3 table instead of a single table. It is because of the ambition to track the source of truth and make data immutable thus helping audit trails.

Ring 1 stores the HASH value therefore making it impossible to upload duplicate files. Ring 2 freezes the uploaded content, therefore we can always go back to what actually came in. Ring 3 is the only working layer. Therefore it is easier to track what was changed and when was it changed and by whom.

This 3 layer architecture enables a robust mechanism for source of truth tracking and immutability.

---

## 2. Filtering Movement Type

Not all record in MB51 is fuel consumed and comes under Scope 1. Therefore it is important to select only those which actually contribute to carbon emission.

Therefore, from my research found out that movement type 201 (cost center) and 261 (production order) represent actual consumption. So used only these 2 values to come under scope 1.

A small tradeoff here is lubricating oil also comes under 201 but since it a very negligible quantity I have ignored for that tradeoff.

---

## 3. Material Classification

The core problem here is there is no universal SAP material code format/standard. This a problem every platform has. We cannot make it universal.

The decision that I have taken is to allow companies to set there material codes that are used in their SAP doc. My model uses a lookup approach rather than hardcoding any codes.

So for every company a specific lookup table is preset which tells the model what material codes means what. Therefore the system becomes more robust and has the ability to handle all SAP material codes. This fixture is provided per client while onboarding.

Other methods like key word matching were rejected because of different languages and formats.

---

## 4. Emission Factor Foreign Key

Instead of just storing the final result we also store a pointer which points to the exact row which was used, exact DEFRA source, year and what value.

Therefore a locked row approved in 2024 will always point to 2024 DEFRA factor and even after 2025 factors are published.

For rows not locked, the factor can be changed and re computed easily. Thus improving audit trail.

---

## 5. Travel Distance Calculation

When only airport codes (IATA codes) are provided the distance needs to calculated differently.

Therefore chose to calculate the distance using the haversine formula which will calculate the circular distance (taking the earth curvature into account) and added a 1.08 uplift factor which the standard issued by ICAO to account for non direct paths of flight and routing inefficiency.

---

## 6. Storing Raw Values as String

Instead of storing the values in a typed value. I store values in JSON format.

This ensure that we do not loose the value which came in. For example: `3.500` stored as decimal would become `3.5`, so we will not know if it meant 3.5 lt or 3500 lt.

Ambiguity is also preserved. For example: a date `4/5/2024` is stored as it is and the analyst can then resolve the date ambiguity (DD/MM or MM/DD).

Type conversion errors during parsing do not corrupt the raw data.

---

## 7. DEFRA as Primary Emission Factor Source

DEFRA was chosen because it is comprehensive (covers all scopes in one doc), updated annually and publicly available. Even though it is UK issued it is now widely used for calculation.

For Indian electricity I have used CEA specifically instead of DEFRA's India figure as CEA published directly from India's actual generation mix data with less lag than DEFRA.

---

## 8. Out of Scope Rows Handling

SAP rows with non consumption movement (anything apart from 201, 261) and non fuel materials are classified Out of scope and stored in RawActivityRow but not in NormalizedActivity. They are visible to analysts in a separate view.

This ensure we do not accidentally filter out some fuel rows, so nothing will be dropped silently.

---

## 9. Billing Period Ambiguity

Sometimes utility billing periods cross months. So I have chosen to assign the it to the start_date.

Other options were day-by-day allocation then dividing across months. This seemed over board and adds to complexity and almost makes minimal difference for a annual report.

---

## 10. Mandatory Comment for Flagged Row

Requires a comment when an analyst accepts a flagged row. This ensure proper reasoning and helps keep track of why it was accepted.

This explanation becomes a permanent part of the audit.

Clean rows do not need comment as the system itself confirmed they are clean.

Without the comment an analyst cannot accept any row.

---

## Additional Decisions

These were some of the key decisions taken during the course of the project. Some smaller but impactful decisions:

- Three User Roles and What each can do
- Application Layer multi tenancy
- Slash Date Format Defaulting (DD/MM/YYYY)
- Two Step Finalization
