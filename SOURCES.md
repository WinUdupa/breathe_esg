SOURCES.md — Data Source Research and Sample Data Documentation
Breathe ESG Intern Assignment

This document covers the three data sources in scope: SAP fuel and procurement data (Scope 1),
utility electricity bills (Scope 2), and corporate travel expenses (Scope 3 Category 6).
For each source it describes the real-world format researched how the sample data was designed to reflect realistic conditions, and what would break
in a production deployment.

================================================================================
SOURCE 1 — SAP FUEL AND PROCUREMENT DATA (SCOPE 1)
================================================================================

REAL-WORLD FORMAT RESEARCHED
------------------------------

SAP does not have one export format. It is an enterprise ERP system with hundreds of
interconnected tables and multiple ways to extract data from it. During research, five
export mechanisms were identified and evaluated:

1. IDoc (Intermediate Document)
   SAP's native format for system-to-system EDI exchange. IDocs are fixed-width positional
   files where each line starts with a segment name (EDI_DC40, E1EDKO1, E1EDP01) and fields
   are at fixed character positions. Designed for SAP-to-SAP integration or SAP-to-EDI-partner
   communication. Requires port configuration, partner profile setup in transaction WE20, and
   a custom fixed-width parser on the receiving end. 

2. OData API (S/4HANA only)
   Modern SAP S/4HANA exposes data through OData REST endpoints. A GET request to the 
   service returns purchase order items as JSON. Requires the
   client to be on S/4HANA, a dedicated API user with specific authorization objects, and network access to the client's SAP
   application server. A typical IT security review for this takes weeks.

3. BAPI / RFC (Remote Function Call)
   SAP function modules exposed for external calling. Requires SAP JCo (Java Connector) or
   pyrfc (Python library), direct port-level network access to the SAP server, and specific
   RFC authorizations. More complex than OData with no data quality advantage.


MB51 was chosen because it is the only format a sustainability coordinator can obtain
independently. Every other format requires either IT team involvement, system-level access,
or direct network connectivity to the SAP server — none of which are realistic for an
onboarding scenario where Breathe ESG is working with a client for the first time.

Critically, MB51 reports actual goods movements — what was actually consumed — not purchase
orders (EKKO/EKPO), which represent intent to buy. A purchase order for 10,000 litres of
diesel does not mean 10,000 litres were burned. A goods issue movement in MB51 means the
fuel left the store and was consumed.

Key SAP tables that MB51 draws from:
  MSEG — Material Document Segments. One row per goods movement line item.
         Contains MATNR (material code), WERKS (plant), BWART (movement type),
         MENGE (quantity), MEINS (unit of measure).
  MKPF — Material Document Header. One row per document.
         Contains BUDAT (posting date), MBLNR (document number).

The flat file export from MB51 produces a delimited file with these fields as column headers,
in the language of the user's SAP GUI session.


WHAT WAS LEARNED
-----------------

Column headers are language dependent.
A user logged into SAP with German as the logon language sees German column headers:
Belegdatum (posting date), Menge (quantity), Einheit (unit), Werk (plant), Bewegungsart
(movement type). The same data exported by a user with English logon shows: Posting Date,
Quantity, Unit, Plant, Movement Type. Any parser must handle both languages for the same
canonical field.

Date format is locale dependent.
European SAP systems export dates as DD.MM.YYYY (15.01.2024). The SAP internal format is
YYYYMMDD (no separators). Some configurations produce DD/MM/YYYY. All three appear in
real exports.

Plant codes are cryptic.
Plant codes (WERKS) are 4-character alphanumeric identifiers configured by each company:
1100, 1200, PL02, HAMB. They carry no inherent location information. The T001W table
in SAP contains the mapping from plant code to plant name, city, and country. Without this
lookup, you cannot assign an emission factor by country or identify where consumption occurred.

Material codes are company-specific.
There is no universal SAP material code standard. HSD-DIESEL-001 at one company is a
completely different material at another. Material classification requires a client-provided
lookup table mapping their specific material codes to fuel types.

Movement types determine transaction type.
Not every row in MB51 represents fuel consumption. Movement type 201 is goods issue to
a cost center (consumption). Movement type 261 is goods issue to a production order
(consumption). Movement type 101 is a goods receipt (the opposite — fuel arriving, not
leaving). Movement type 202 is a reversal of a previous goods issue. Only 201 and 261
represent actual consumption for Scope 1 purposes.

Units of measure are inconsistent.
The same fuel type can appear in different units across different plants. Diesel may be
in litres at one plant, US gallons at another, kilograms at a third. All must convert
to a common energy unit (Megajoules) before emission factors can be applied.


SAMPLE DATA DESIGN
-------------------

File: sap_mb51_q1_2024.csv
Format: Comma-delimited, UTF-8 encoded, English headers, DD.MM.YYYY dates
Rows: 21 (including header)
Data rows: 20 (covering January–March 2024)

The file was designed to contain realistic fuel consumption records from a company
operating across multiple plants in India, Germany, and the UK, alongside deliberate
edge cases that test every parser and normalizer code path.

Normal rows cover:
- Diesel consumption (HSD-DIESEL-001) across plants 1100, 1200, 1300, 1400
- Petrol consumption (MS-PETROL-002) at plant 1200
- Natural gas consumption (NATGAS-PIPE-004) at plant 1100 in M3
- LPG consumption (LPG-BULK-003) at plants 1100 and 1300 in KG
- Quantities in the realistic range of 980–5100 litres or equivalent per month
- All movement types 201 or 261

Edge cases deliberately included:

  Number format ambiguity (row 6)
  Quantity shown as 3.500 — the European thousands separator notation that means
  3500 litres, not 3.5 litres. Tests the number parser's ability to detect and handle
  European number formatting and flag it for analyst confirmation.

  Reversal movement type (row 7 in original file)
  Movement type 202 with a negative quantity. Should be classified as OUT_OF_SCOPE
  before normalization — it is a reversal of a previous goods issue, not a new
  consumption event.

  Goods receipt (row 12 in original file)
  Movement type 101. Fuel arriving at the warehouse. Not a consumption event.
  Should be classified as OUT_OF_SCOPE.

  Unknown material (row 10)
  Material code 9000456 is not in the MaterialGroupLookup fixture. Represents a real
  scenario where a company's SAP contains materials that have not been classified.
  Should flag MATERIAL_UNCLASSIFIED and produce null CO2e.

  Quantity spike (row 11)
  50,000 litres of diesel at plant 1400 — approximately 10 times the average for
  other diesel rows in the file. Represents either a real event (new generator, large
  construction project) or a data entry error (extra zero). Should trigger OUTLIER_HIGH
  flag. CO2e is still computed — the flag asks the analyst to confirm, not reject.

  GAL unit (row 13)
  1500 US gallons of petrol. Requires a two-step conversion: GAL to litres (multiply
  by 3.785), then litres to MJ using the petrol energy density factor. Tests the
  multi-step unit conversion logic.

  Future date and old date (rows in test file)
  Dates outside the FY2024 reporting period. Should flag DATE_OUTSIDE_PERIOD and
  fail to auto-assign a reporting period.


WHAT WOULD BREAK IN PRODUCTION
--------------------------------

Custom Z-fields.
Many SAP implementations add company-specific custom fields to standard tables — called
Z-fields (ZZCARBON_CATEGORY, ZZENERGY_TYPE). These appear as extra columns in MB51
exports. The current parser ignores unknown columns, but a client who uses Z-fields
for fuel classification would need custom column mapping configured per client.

Company-specific material codes not in fixture.
Every client onboarded will have different material codes. The MaterialGroupLookup fixture
must be populated per client during onboarding. This is a manual exercise that requires
the client to provide a list of their fuel material codes, which most sustainability
coordinators do not have readily available — it requires going back to the SAP team.

Multiple SAP instances.
A global company may run SAP ECC 6.0 in Europe, SAP S/4HANA in the US, and a legacy
system in Asia. Each produces exports with different column names, date formats, and
number formats. Each would need a separate parser configuration.

Movement types outside 201 and 261.
Some companies configure custom movement types for fuel consumption (Z01, Z61). These
would be classified as OUT_OF_SCOPE by the current system, silently excluding real
consumption data. The system flags them for analyst visibility but does not compute
their emissions.

Diesel and petrol in kilograms.
Some tanks measure by weight rather than volume. Converting KG to litres requires
a density factor that varies by temperature and fuel grade. This system does not
support KG to litre conversion for liquid fuels — those rows flag CONVERSION_FACTOR_MISSING.

Actual consumption vs purchase orders.
MB51 captures goods movements, not actual combustion. A goods issue of 5000 litres
to a cost center means 5000 litres left the store. It does not confirm all 5000 litres
were burned — some may remain in equipment fuel tanks at period end. A fully accurate
Scope 1 calculation would require tank inventory adjustments. This system treats goods
issue quantities as consumed quantities, which is standard practice for annual reporting
but introduces a small systematic bias.


================================================================================
SOURCE 2 — UTILITY ELECTRICITY BILLS (SCOPE 2)
================================================================================

REAL-WORLD FORMAT RESEARCHED
------------------------------

Four modes of accessing utility electricity data were evaluated:

1. Green Button XML
   A US Department of Energy standard for energy data portability. Utilities provide data
   in XML format following the IEC 61968-9 CIM schema. Contains interval-level readings, 
   tariff structures, and billing metadata. Two variants:
   Green Button Download My Data (DMD) — user downloads from portal, and Green Button
   Connect My Data (CMD) — API-based automated data sharing.

   Rejected because: Green Button is primarily a US standard. Indian utilities (BESCOM,
   MSEDCL, TNEB, MSEB, KSEB) do not support it. Even among US utilities, adoption is
   inconsistent. The interval-level data it provides is far more granular than annual
   emissions reporting requires — monthly totals are sufficient. Parsing Green Button XML
   requires handling XML namespaces, nested structures, and the IEC schema.

2. PDF Bills
   The format most commonly received by facility managers from smaller utilities. Every
   utility produces PDFs with different layouts.

   Rejected because: Parsing requires OCR for scanned bills and layout-aware extraction
   for digital PDFs. BESCOM's bill layout is completely different from MSEDCL's. A PDF
   parser that works for one utility fails for another. High failure rates, significant
   engineering effort, documented as a tradeoff.

3. Direct Utility API
   Some utilities offer APIs (Green Button Connect in the US, some European utilities).

   Rejected because: Indian utilities do not offer public APIs. Even where APIs exist,
   integration requires per-utility OAuth credentials and utility-specific documentation.

4. Portal CSV Export (CHOSEN)
   Every major Indian utility provides a CSV download from their online customer portal.
   Facility managers download this as part of their regular billing process.

   BESCOM (Bangalore Electricity Supply Company) — serves Bangalore and surrounding areas.
   Portal at bescom.org provides monthly usage CSV downloads per meter.

   MSEDCL (Maharashtra State Electricity Distribution Company) — serves Maharashtra
   including Mumbai and Pune. Portal provides billing history as CSV.

   TNEB (Tamil Nadu Electricity Board) — serves Tamil Nadu including Chennai.
   Portal provides consumption history as downloadable CSV.

   Portal CSV was chosen because it is the actual handoff format. A sustainability
   coordinator at a client company does not receive Green Button XML or API responses.
   They receive a CSV that a facilities manager downloaded from the utility portal.
   Building a system that accepts the format people actually have is better product
   thinking than building one that accepts the format that would be technically elegant.


WHAT WAS LEARNED
-----------------

No universal CSV format exists.
Each utility has different column names, column ordering, and date formats. BESCOM calls
the consumption column "Usage (kWh)". MSEDCL may call it "Consumption" or "Units". TNEB
may use "Energy Consumed". A parser must map multiple header variants to the same
canonical field name.

Date formats vary across and within utilities.
BESCOM's portal exports DD/MM/YYYY. Some MSEDCL exports use YYYY-MM-DD. TNEB's portal
historically used DD-Mon-YYYY (01-Jan-2024). The same facility may have bills in multiple
date formats if they switched billing systems during the reporting period.

Billing periods do not align with calendar months.
A utility does not read every meter on the first of the month. Meter readers have routes
that take several days. A "January bill" may cover December 3 to January 2. Another meter
at the same facility may be read on different dates, so its January bill covers January 8
to February 7. For annual reporting this is manageable, but for monthly dashboards it
creates allocation problems.

Actual vs estimated reads.
Utilities do not always read meters in person. When a meter reader cannot access a location
(locked gate, equipment, weather), the utility estimates consumption based on historical
patterns. Bills mark readings as Actual or Estimated. Estimated reads should be flagged for
analyst attention — they may need to be corrected once the actual reading arrives.

Multiple meters per facility.
A large industrial facility has multiple meters — main supply, HVAC submeter, production
line meters. Each meter has its own account number and billing cycle. Summing them correctly
requires a facility grouping concept.

Usage spikes can be legitimate or errors.
A usage spike of 10× normal for a meter could be a new production line coming online or
an extra zero in the data. The system cannot know which. It flags statistical outliers for
analyst confirmation without blocking the calculation.

Country-specific emission factors matter.
India's electricity grid is coal-heavy. The CEA 2024 grid emission factor for India is
0.708 kgCO2e/kWh. The UK grid is much cleaner at 0.207 kgCO2e/kWh. Germany is 0.380.
Using a global average for Indian facilities would significantly understate Scope 2 emissions.
Using country-specific factors wherever they exist is more accurate and more defensible to
auditors. Where no country-specific factor exists, the system uses a global fallback
(0.475 kgCO2e/kWh from IEA data) and flags the row.


SAMPLE DATA DESIGN
-------------------

File: utility_test.csv (extended test)
Format: Comma-delimited, UTF-8 encoded
Facilities: Multiple facilities across India and Germany

The file was designed to cover realistic multi-meter, multi-facility electricity billing
data with deliberate edge cases testing every normalizer code path.

Normal rows cover:
- Four Indian facilities across Bangalore (BESCOM), Pune (MSEDCL), Chennai (TNEB),
  and Mumbai (MSEDCL)
- German facility under EnBW Stuttgart
- Realistic monthly consumption ranges per facility type
- Mix of date formats matching what each utility actually produces
- Account numbers prefixed with utility identifiers (KA-BESCOM, MH-MSEDCL, TN-TNEB,
  DE-ENBW) reflecting real account number conventions

Edge cases deliberately included:

  Three date formats in one file
  DD/MM/YYYY (Indian utilities), YYYY-MM-DD (German utility, ISO standard), and
  DD-Mon-YYYY (TNEB historical format). All three must parse correctly. Tests the
  multi-format date parser.

  Billing period crossing calendar month (Pune facility)
  Period Start 05/04/2024, Period End 05/05/2024. Assigned entirely to April per
  the period_start decision. Tests that the system correctly assigns cross-month
  bills without splitting.

  Billing period overlap (same meter, overlapping dates)
  Two bills for MTR-PNQ-0088 with overlapping date ranges. Should flag
  BILLING_PERIOD_OVERLAP — a data quality issue indicating either a data entry error
  or a billing correction that was not properly handled.

  Estimated read
  One row with Read Type = Estimated. Should flag READ_ESTIMATED. CO2e is still
  computed — the flag asks the analyst to confirm whether to accept the estimate
  or wait for the actual read.

  Consumption spike (285,000 kWh)
  One meter showing 285,000 kWh in a month where its previous two months were
  approximately 30,000 kWh. Should flag OUTLIER_HIGH. Represents either equipment
  added to the meter or a data error.

  Empty usage field
  One row with no value in the usage column. Should flag MISSING_QUANTITY and
  produce null CO2e. Tests that empty fields are handled without crashing.

  Duplicate row
  Two identical rows with the same meter, same billing period, same usage. Should
  flag DUPLICATE_SUSPECTED. Represents a common real-world scenario where a facilities
  team exports and re-imports the same data.

  German facility rows
  Three rows from a Stuttgart facility under EnBW. Tests country detection from
  the service address and correct application of the German grid emission factor
  (0.380 kgCO2e/kWh) rather than the Indian factor.


WHAT WOULD BREAK IN PRODUCTION
--------------------------------

Per-utility column mapping.
Each utility's CSV has different column names. The current system maps common header
variants to canonical names. A utility with a completely non-standard header (for example,
BESCOM changing their export format in a software update) would produce parse errors for
all columns. In production, a configuration layer would specify column mappings per utility.

Solar net metering.
Facilities with on-site solar generation receive bills showing grid import minus solar
export — the net figure. For Scope 2, the gross grid import is what matters (some solar
export accounting frameworks require separate treatment of generation and consumption).
The current system treats the usage field as-is. If a client's bills show net consumption,
Scope 2 emissions would be understated.

Demand response credits.
Commercial customers who participate in demand response programs (reducing consumption
during grid peaks) receive credits that appear as negative line items in their bills.
The current system would flag these as NEGATIVE_QUANTITY. Business logic to distinguish
demand response credits from data errors is not implemented.

Time-of-use tariffs.
Some utilities split bills into multiple rows per meter per month for peak and off-peak
periods. The current system would treat each row as a separate billing period, creating
apparent gaps and overlaps. Aggregation by meter and period before normalization would
be needed.

Meter replacements.
When a utility replaces a meter, the account continues but the meter ID changes. Billing
period gap detection compares meter IDs — a meter replacement would appear as a gap on
the old ID and a new start on the new ID, falsely triggering BILLING_PERIOD_GAP.

International utility formats beyond what is seeded.
The emission factor table covers India, UK, US, and Germany. A client with facilities in
Japan, Australia, or the Middle East would trigger EMISSION_FACTOR_FALLBACK on all their
electricity rows. Production would require emission factors for every country where
the client operates.


================================================================================
SOURCE 3 — CORPORATE TRAVEL (SCOPE 3 CATEGORY 6)
================================================================================

REAL-WORLD FORMAT RESEARCHED
------------------------------

The corporate travel data source was researched by examining the SAP Concur platform,
which is the dominant corporate travel and expense management system globally, and
comparing it with Navan (formerly TripActions), a newer competitor with significant
adoption among technology companies.

Research examined:
  Concur Developer Center documentation (developer.concur.com)
  Concur Expense Reports API v3 endpoint structure and response schema
  Concur Receipts API JSON schemas for air-receipt, hotel-receipt, and
  ground-transport-receipt
  Navan API documentation via the Fivetran connector documentation
  Real-world Concur CSV export format from standard expense report extraction

The Concur API has two relevant endpoints for emissions data:

  GET /api/v3.0/expense/reports
  Returns report-level metadata — submitter, approval status, totals.
  Does not contain individual expense line items.

  GET /api/v3.0/expense/entries?reportID={id}
  Returns line items for a specific report — expense type, date, amount,
  merchant, and custom fields.

The critical finding from API research: airport codes for origin and destination are
not standard fields in Concur's expense entry schema. They are stored in custom fields
(Custom1, Custom2, etc.) that each company configures independently. Whether a Concur
export contains structured airport code data depends entirely on whether the company's
Concur administrator configured those custom fields and whether employees used them
correctly. Many companies do not. Employees book a flight, expense it as "Airfare",
and the origin and destination exist only in the airline receipt attached as a PDF.

CSV export was chosen over API integration for the same practical reason as SAP:
API integration requires corporate-level OAuth credentials. A sustainability team
does not have Concur API access. They have a CSV that the finance team exported from
the expense reporting module.

The CSV format was modeled on Concur's standard expense export structure, extended
with explicit columns for origin, destination, cabin class, round trip flag, hotel
city, hotel country, check-in and check-out dates, and distance — fields that
a well-configured Concur export or a Navan export would contain.


WHAT WAS LEARNED
-----------------

Expense type naming is not standardised.
Different companies configure different expense type names in Concur. One company uses
"AIRFR" (the Concur default code), another uses "Flight", another uses "Air Travel",
another uses "International Air". A parser must map case-insensitive variants of common
names to canonical types: flight, air, airfare → FLIGHT. Hotel, lodging, accommodation
→ HOTEL. Taxi, rideshare, uber, ola, train, rail, car rental → GROUND.

Airport codes are not always present.
Employees who book through the corporate travel platform have structured booking data
including airport codes. Employees who book personally and expense later typically have
no structured data — just a description ("Mumbai to London flight") and an amount.
The system cannot extract airport codes from free text. Those rows flag IATA_CODE_NOT_FOUND
and produce null CO2e until the analyst provides the missing information.

Cabin class is frequently missing.
Expense reports capture the cost, date, and route of a flight. Cabin class requires either
the airline receipt or the booking record. If an employee books economy and upgrades at
the gate, the expense report may show the original booking class not the actual class flown.
The system defaults to Economy and flags CABIN_CLASS_ASSUMED when cabin class is absent.

Distance is never provided for ground transport.
A taxi receipt has date, merchant (taxi company), and amount. It does not have distance.
Without distance, emissions cannot be computed from first principles. Spend-based proxy
calculations (dividing spend by average cost per km) are not defensible for audit. The
system flags DISTANCE_UNAVAILABLE and leaves CO2e null for ground transport without
explicit distance.

Flight distance requires calculation, not lookup.
Concur does not compute distances. The system receives origin and destination IATA codes
and must compute the distance itself using the Great Circle Distance (haversine) formula.
The haversine result is the shortest path between two points on a sphere — planes do not
fly perfectly straight paths, so ICAO recommends a 1.08 uplift factor to account for
routing inefficiency. The uplifted distance is used for emission factor application.

Radiative Forcing Index is already incorporated in DEFRA flight factors.
Aviation at altitude has a warming effect beyond CO2 alone — contrails, NOx, and water
vapour at altitude multiply the effective warming. This is captured by the Radiative
Forcing Index (approximately 1.9×). DEFRA's published flight emission factors already
incorporate RFI. No separate multiplier is applied — using DEFRA factors gives the
full warming impact automatically.

Hotel emission factors vary significantly by country.
DEFRA publishes country-specific hotel emission factors. A hotel night in India (0.708
kgCO2e/kWh grid, high energy use per room) has a factor of 38.8 kgCO2e per room-night.
A hotel night in the UK (0.207 kgCO2e/kWh grid, energy efficiency regulations) has a
factor of 6.2 kgCO2e per room-night. Using a global average (10.4) for all countries
would significantly misstate emissions for India-heavy travel portfolios.

Round trips double passenger-kilometres.
A return flight BOM–LHR–BOM is twice the one-way distance in passenger-kilometres.
Travel platform exports handle round trips inconsistently: some export as a single row
with a round trip flag, others export as two rows (outbound, return). The system handles
the single-row with flag approach by multiplying passenger-km by 2.


SAMPLE DATA DESIGN
-------------------

File: travel_2024.csv (original) and travel_test.csv (extended test)
Format: Comma-delimited, UTF-8 encoded
Rows: Mix of flights, hotels, and ground transport

The file was designed to reflect the actual complexity of a real corporate travel export
from a mid-size Indian company with some international travel. Expense type names use
mixed case (Flight not FLIGHT, Hotel not HOTEL, Car Rental not CAR_RENTAL) to reflect
real-world Concur configuration where names are human-entered.

Normal rows cover:
- Domestic short-haul flights within India (BLR→DEL, DEL→BOM, PNQ→CCU)
- International long-haul flights (BOM→LHR, BOM→SFO, DEL→SIN)
- Hotels in India (New Delhi), UK (London), UAE (Dubai), USA (San Francisco)
- Ground transport including taxi, train (BLR→MAS), and car rental
- Mix of Economy, Business, and First class cabin assignments
- Both one-way and round-trip flights
- Amounts in INR reflecting India-based company

Edge cases deliberately included:

  Pre-filled distance (BLR→DXB, 1740 km)
  Some companies pre-compute distances in their export. When distance is provided,
  the system uses it directly rather than computing haversine. Tests the "use provided
  distance" code path and avoids overriding accurate source data with an approximation.

  Unknown IATA code (ZZZ)
  An airport code not in the system's airport fixture. Should flag IATA_CODE_NOT_FOUND
  and produce null CO2e. Represents the common scenario of an employee flying through
  a smaller regional airport not in the hardcoded fixture.

  Missing cabin class (BOM→JFK)
  No cabin class specified. System defaults to Economy and flags CABIN_CLASS_ASSUMED.
  CO2e is still computed using the Economy factor.

  Brazil hotel (São Paulo)
  Hotel country "Brazil". No Brazil-specific hotel emission factor exists in the seed
  data. Should flag EMISSION_FACTOR_FALLBACK and use the global average of 10.4
  kgCO2e per room-night. Tests country resolution for non-seeded countries.

  Duplicate flight rows (PNQ→CCU, identical)
  Two identical rows representing the same expense entered twice — a common error when
  employees or finance teams process the same export multiple times. Should flag
  DUPLICATE_SUSPECTED on the second occurrence.

  Negative distance (Car Rental, -120 km)
  Distance field contains a negative value. Physically impossible. Should flag
  DISTANCE_UNAVAILABLE (negative treated as invalid) and produce null CO2e.

  Taxi with distance in overflow column
  The last taxi row had its distance value shifted into an unmapped column due to an
  extra comma in the CSV row — a very common real-world CSV formatting issue. Identified
  and fixed by improving the column mapping to handle overflow columns.

  Hotel with no transaction date (London hotel)
  The Date column is empty. Check-in and check-out dates are present so nights can
  be computed. activity_period_start is null, which should flag DATE_OUTSIDE_PERIOD.
  Tests that the system handles partial date information without crashing.

  Train classified as ground transport (BLR→MAS)
  Expense type "Train" with distance 350 km. Should be classified as TRAVEL_GROUND
  and use the rail emission factor (0.03546 kgCO2e/pkm), not the taxi factor.
  CO2e: 350 × 0.03546 = 12.4 kgCO2e.


WHAT WOULD BREAK IN PRODUCTION
--------------------------------

Custom field mapping varies per Concur deployment.
Airport origin and destination codes are stored in custom fields. The specific custom
field numbers (Custom1, Custom2) vary per company — one company uses Custom3 and Custom4.
In production, a configuration layer would specify which custom fields contain which
data for each client's Concur setup.

Non-Concur travel platforms.
Navan, TravelPerk, Egencia, and BCD Travel all produce different CSV formats with
different column names, different expense type codes, and different data structures.
The current parser handles Concur-style exports. A client using Navan would require
either a separate parser or a format adapter.

Airline class codes vs text descriptions.
Airlines use letter codes for cabin classes: Y (economy), B/M/H (economy fare buckets),
W (premium economy), C/J/D (business), F/A (first). Concur sometimes exports these
codes rather than plain text descriptions. The current cabin class mapping handles
text descriptions. A Concur export with raw airline codes would fail to map and default
to Economy with CABIN_CLASS_ASSUMED.

Multi-leg flights exported as one row.
A flight from BOM to SFO via DXB may be exported as one expense row (BOM to SFO,
total cost) or three rows (BOM-DXB leg 1, DXB-SFO leg 2, and a return). The current
system treats each row as a single non-stop flight. For multi-leg flights exported as
one row, haversine computes the direct BOM-SFO distance, ignoring the via-DXB routing,
which slightly understates the actual flight distance.

Employees booking outside the corporate travel platform.
Employees who book directly with airlines or through personal accounts and expense
reimbursement typically provide only amount, date, and a free-text description. No
structured origin/destination data. The system cannot process these rows without
analyst intervention to supply the missing IATA codes.

Airport fixture covers 12 airports only.
The hardcoded airport fixture contains 12 major Indian and international airports.
Any flight involving a regional airport, secondary city airport, or less common
international hub would trigger IATA_CODE_NOT_FOUND. Production would use the full
OurAirports dataset (9,000+ airports with coordinates) as a database fixture.

Hotel emission factors for non-seeded countries.
The seed data contains hotel factors for India and the UK only. Travel to any other
country triggers EMISSION_FACTOR_FALLBACK and uses the global average. A company with
significant travel to the US, Germany, Singapore, or Australia would benefit from
country-specific hotel factors — these exist in the DEFRA international factors dataset
and could be added to the seed data.

================================================================================

================================================================================
