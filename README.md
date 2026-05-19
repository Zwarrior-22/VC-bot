```markdown
# **MarketPulse: Automated Venture Intelligence Pipeline**

**MarketPulse** is a lightweight, hyper-leveraged venture sourcing pipeline designed to consume the execution tax of deal flow tracking. Instead of relying on manual information routing, it continuously ingests raw, unstructured data from across the tech ecosystem, running an on-the-fly analytical layer to map findings directly to core investment theses.

---

## **Technical Architecture Overview**

* **Data Ingestion Layer:** Concurrent parsing of RSS feeds and ecosystem APIs (including structured HackerNews `Launch HN` endpoint strings).
* **NLP & Analytical Layer:** Integrated VADER (Valence Aware Dictionary and sEntiment Reasoner) sentiment classification via `NLTK` to score market signal intensity.
* **Deterministic Deduplication:** State tracking utilizing $O(1)$ memory lookup loops to filter out operational data duplication before network syncing.
* **Storage Syncing:** Dynamic worksheet provisioning and batched payload distribution integrated with the Google Sheets API, featuring `HTTP 429` rate-limiting back-off recovery.

---

## **Required Dependencies**

Ensure your local runtime environment or cloud worker has the following packages installed:

```bash
pip install requests feedparser gspread google-auth pandas nltk

```

---

## **Step 1: Set up Google Cloud & Service Account**

To establish programmatic authentication for the script's automated syncing layer, configure a dedicated GCP service account:

1. **Access Google Cloud Console:** Navigate to [console.cloud.google.com](https://console.cloud.google.com/).
2. **Initialize Project:** Click the project dropdown menu at the top, select **"New Project"**, name it `MarketPulse`, and initialize it.
3. **Enable API Ecosystems:** * Search for **"Google Drive API"** in the top search bar and click **"Enable"** (required for file-level scoping).
* Search for **"Google Sheets API"** and click **"Enable"**.


4. **Provision Service Account:**
* Navigate to **"Service Accounts"** via the search bar.
* Select **"+ Create Service Account"**. Name it `marketpulse-pipeline-node`.
* **IAM Permissions (Critical):** Under "Role", assign **"Project" > "Editor"** to grant operational clearance within the scope of this project. Click **Done**.


5. **Generate Private Key (credentials.json):**
* Select your newly created service account from the list. Click the three-dot action menu and choose **"Manage keys"**.
* Click **"Add Key" > "Create new key"**, choosing **JSON** as the structure type.
* Download the file, rename it exactly to `credentials.json`, and place it in the root directory of the repository alongside the main script.



---

## **Step 2: Initialize Storage Endpoint**

1. **Provision Spreadsheet:** Navigate to [sheets.google.com](https://sheets.google.com/) and spin up a clean worksheet.
2. **Extract Sheet ID:**
* Isolate the unique resource identifier string embedded within your browser's URL path.
* *Example URL:* `https://docs.google.com/spreadsheets/d/1X1bVNsZJLB9hHX-l7T0hLrb4d_R3BCJyfeJAtpDComk/edit`
* *Target ID:* `1X1bVNsZJLB9hHX-l7T0hLrb4d_R3BCJyfeJAtpDComk`


3. **Authorize Pipeline Access:**
* Open your local `credentials.json` file and extract the `"client_email"` string value (e.g., `marketpulse-pipeline-node@...iam.gserviceaccount.com`).
* Return to your Google Sheet interface, click **Share** in the upper-right corner, paste the client email address, and grant it explicit **Editor** permissions.



---

## **Step 3: Running the Pipeline**

1. Ensure `vc_dealflow_bot.py` and your authorized `credentials.json` are paired within the exact same root path.
2. Open `vc_dealflow_bot.py` and paste your extracted resource identifier directly into the global configuration variable:
```python
GOOGLE_SHEET_ID = "YOUR_EXTRACTED_SHEET_ID_HERE"

```


3. Execute the orchestration pipeline from your terminal:
```bash
python vc_dealflow_bot.py

```



### **Automated Lifecycle Processing:**

* **First Run:** The script interfaces with your target sheet, automatically checks for structural compatibility, dynamically provisions new isolated sheets for configured investment theses (`AI & ML`, `Future of Data`, `Developer Tools`, `General B2B`), and stamps out a 7-column matrix: `['Source', 'Company/Title', 'Description', 'Link', 'Date Found', 'Published Date', 'Sentiment Score']`.
* **Subsequent Executions:** The script queries existing states, drop-filters previously cataloged source links, evaluates incoming startup updates for keyword matches, applies sentiment polarity rankings, and appends the new signals into your live dashboard.

```

```
