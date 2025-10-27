# **VC Deal Flow Bot: Setup Guide**

You MUST follow these steps to get the vc\_dealflow\_bot.py script to run. This guide will walk you through setting up the necessary Google Cloud and Google Sheets permissions.

## **Required Python Libraries**

First, you need to install the required Python libraries.

pip install requests feedparser gspread google-auth pandas

## **Step 1: Set up Google Cloud & Service Account**

The script needs a "service account" (a robot user) to automatically edit your Google Sheet.

1. **Go to the Google Cloud Console:** [console.cloud.google.com](https://console.cloud.google.com/)  
2. **Create a New Project:**  
   * Click the project dropdown at the top of the page and select "New Project".  
   * Give it a name, like "VC Sourcing Bot", and click "Create".  
3. **Enable the Google Drive & Google Sheets APIs:**  
   * In the search bar at the top, search for and select **"Google Drive API"**. Click **"Enable"**. (This is still needed for the service account to have file-level permissions).  
   * Do the same for **"Google Sheets API"**. Search for it and click **"Enable"**.  
4. **Create a Service Account:**  
   * In the search bar, search for and select **"Service Accounts"**.  
   * Click **"+ Create Service Account"** at the top.  
   * Give it a name (e.g., "sheets-editor-bot") and a description. Click "Create and Continue".  
   * **Grant Access (Important):** For "Role", select **"Project" \> "Editor"**. This gives it permission to *act* within your project.  
   * Click "Continue", then "Done".  
5. **Get Your Credentials File (credentials.json):**  
   * You should now see your new service account in the list. Click the three-dot "Actions" menu on the right and select **"Manage keys"**.  
   * Click **"Add Key" \> "Create new key"**.  
   * Choose **JSON** as the key type and click **"Create"**.  
   * A file will automatically download. **Rename this file to credentials.json** and place it in the **exact same folder** as your vc\_dealflow\_bot.py script.

## **Step 2: Set up Your Google Sheet**

1. **Create a New Google Sheet:** Go to [sheets.google.com](https://sheets.google.com/) and create a new, blank sheet. You can name it anything you like (e.g., "VC Deal Flow").  
2. **Get the Sheet ID (CRITICAL):**  
   * Look at the URL in your browser. The Sheet ID is the long string of letters and numbers in the middle.  
   * **Example URL:** https://docs.google.com/spreadsheets/d/**1X1bVNsZjhNnx-T7-t0HLrb4cL\_R38cfeylAtpDComk**/edit  
   * **Your ID is:** 1X1bVNsZjhNnx-T7-t0HLrb4cL\_R38cfeylAtpDComk  
   * Copy this ID. You will need it in the next step.  
3. **Share the Sheet (CRITICAL):**  
   * Open your credentials.json file.  
   * Find the line that looks like "client\_email": "your-bot-name@...iam.gserviceaccount.com".  
   * Copy this entire email address.  
   * Go back to your Google Sheet and click the **"Share"** button (top right).  
   * Paste the service account's email address into the "Add people and groups" box.  
   * Make sure it has the **"Editor"** role, and click **"Send"** (you can uncheck "Notify people").

## **Step 3: Run the Script**

You're all set\!

1. Make sure your vc\_dealflow\_bot.py and credentials.json are in the same directory.  
2. Open vc\_dealflow\_bot.py and paste your **Sheet ID** into the GOOGLE\_SHEET\_ID variable at the top of the file (around line 14).  
3. Run the script from your terminal:

python vc\_dealflow\_bot.py

The first time it runs, it will create a new tab (worksheet) called "Sourced Startups", add a header, and then populate it with all the relevant startups it finds. The next time you run it, it will only add the *new* ones.