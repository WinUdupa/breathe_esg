# Breathe ESG — Carbon Emission Tracker

A data ingestion and analyst review system for tracking Scope 1, 2, and 3 carbon emissions.
Accepts SAP fuel data, utility electricity bills, and corporate travel logs. Normalizes,
flags, and routes data through an analyst review workflow before audit lock.

---

## Live App

**URL:** https://breathe-esg-frontend-urta.onrender.com

---

## Login Credentials

| Role | Username | Password |
|---|---|---|
| Uploader | uploader1 | breathe123 |
| Analyst | analyst1 | breathe123 |
| Admin | admin1 | breathe123 |

---

## How to Use

### As Uploader
1. Log in as `uploader1`
2. Select a source type — SAP Fuel, Utility Electricity, or Corporate Travel
3. Upload the corresponding CSV file
4. Track upload status in the history table below

### As Analyst
1. Log in as `analyst1`
2. Click **Review** on any pending upload
3. Review scope summary — see total rows and flagged count per scope
4. Click **Review Scope 1 / 2 / 3** to enter the row table
5. Flagged rows appear at the top — click **Review** to open the detail panel
6. Read the flag explanation, raw values, and calculated CO2e
7. Type a comment and click **Accept** or **Reject**
8. Use **Approve All Clean Rows** to bulk accept non-flagged rows
9. Once all flagged rows are resolved, click **Submit for Admin Review**

### As Admin
1. Log in as `admin1`
2. Click **Review & Finalize** on any analyst-approved upload
3. Browse rows (read-only)
4. Click **Finalize Upload** and confirm to permanently lock all records

---

## Sample Data Files

Located in `backend/sample_data/`

| File | Source Type |
|---|---|
| `sap_mb51_q1_2024.csv` | SAP Fuel & Procurement |
| `utility_jan_dec_2024.csv` | Utility Electricity |
| `travel_2024.csv` | Corporate Travel |

---

## Local Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver

# Frontend
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`
Backend runs at `http://localhost:8000`
