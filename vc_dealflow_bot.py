import requests
import feedparser
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
from datetime import datetime
import time

# --- CONFIGURATION ---
# *** 1. UPDATE THIS WITH YOUR SHEET ID ***
#    Get this from the URL of your Google Sheet:
#    https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
#
#    Based on your screenshot, your ID is: 1X1bVNsZjhNnx-T7-t0HLrb4cL_R38cfeylAtpDComk
GOOGLE_SHEET_ID = "1X1bVNsZJLB9hHX-l7T0hLrb4d_R3BCJyfeJAtpDComk"
WORKSHEET_NAME = "Sourced Startups"





FILTER_KEYWORDS = [
    'ai', 'ml', 'saas', 'b2b', 'fintech', 'api', 'devops', 
    'developer tool', 'cybersecurity', 'open-source'
]


SERVICE_ACCOUNT_FILE = 'credentials.json'

# --- DATA SOURCES ---
TECHCRUNCH_RSS_URL = 'https://techcrunch.com/feed/'
YCOMBINATOR_LAUNCHED_RSS_URL = 'https://www.ycombinator.com/blog/launched/rss'
# Uses the Algolia API, which is the official search API for HN
HACKERNEWS_LAUNCH_HN_API = "http://hn.algolia.com/api/v1/search_by_date?query=Launch%20HN&tags=story"

# --- GOOGLE SHEETS SETUP ---

def setup_google_sheets():
    """
    Connects to the Google Sheets API using service account credentials
    and opens the correct worksheet.
    """
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Open the sheet by its ID (key)
        print(f"Attempting to open Google Sheet by ID: '{GOOGLE_SHEET_ID}'...")
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        # Try to open the worksheet, create it if it doesn't exist
        try:
            worksheet = sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            print(f"Worksheet '{WORKSHEET_NAME}' not found. Creating it...")
            worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="20")
            
            # Add header row
            header = ['Source', 'Company/Title', 'Description', 'Link', 'Date Found', 'Published Date']
            worksheet.append_row(header)
            print("Worksheet created and header row added.")
            
        print(f"Successfully connected to Google Sheet > '{WORKSHEET_NAME}' tab")
        return worksheet
        
    except APIError as e:
        print("\n--- ERROR: API ERROR ---")
        if "PERMISSION_DENIED" in str(e):
             print("The service account has 'PERMISSION_DENIED'.")
             print("This means the Google Sheets API is working, but your service account is not an 'Editor' on the sheet.")
             print("Please double-check your 'Share' settings on the Google Sheet.")
        elif "NOT_FOUND" in str(e) or "Spreadsheet not found" in str(e):
             print(f"Error: The Google Sheet with ID '{GOOGLE_SHEET_ID}' was not found.")
             print("Please double-check that your GOOGLE_SHEET_ID is correct and has no typos.")
        else:
             print(f"An API error occurred: {e}")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please ensure 'credentials.json' is correct and your 'GOOGLE_SHEET_ID' is correct.")
        return None

def get_existing_links(worksheet):
    """
    Fetches all links from the 'Link' column (column 4) to avoid duplicates.
    """
    try:
        links = worksheet.col_values(4)  # 4th column is 'Link'
        return set(links)
    except Exception as e:
        print(f"Warning: Could not fetch existing links. May create duplicates. Error: {e}")
        return set()

# --- DATA FETCHING ---

def fetch_rss_feed(url, source_name):
    """
    A generic function to fetch and parse an RSS feed.
    Returns a list of startup dictionaries.
    """
    print(f"Fetching from {source_name}...")
    startups = []
    feed = feedparser.parse(url)
    
    for entry in feed.entries:
        startups.append({
            'source': source_name,
            'title': entry.title,
            'description': entry.get('summary', 'No description'),
            'link': entry.link,
            'published_date': entry.get('published', 'N/A')
        })
    print(f"Found {len(startups)} total posts from {source_name}.")
    return startups

def fetch_hackernews_launches():
    """
    Fetches "Launch HN" posts from the HackerNews Algolia API.
    Returns a list of startup dictionaries.
    """
    print("Fetching from HackerNews 'Launch HN'...")
    startups = []
    try:
        response = requests.get(HACKERNEWS_LAUNCH_HN_API)
        response.raise_for_status()  # Raise an error for bad responses
        hits = response.json().get('hits', [])
        
        for hit in hits:
            title = hit.get('title', 'No Title')
            # Use story_url if available, otherwise the main HN link
            link = hit.get('story_url') or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            
            # Clean up the title
            if title.startswith("Launch HN: "):
                title = title.replace("Launch HN: ", "")
                
            startups.append({
                'source': 'HackerNews Launch',
                'title': title,
                'description': f"HN Comments: {hit.get('num_comments', 0)}. Points: {hit.get('points', 0)}.",
                'link': link,
                'published_date': datetime.fromtimestamp(hit.get('created_at_i', 0)).isoformat()
            })
        print(f"Found {len(startups)} total posts from HackerNews.")
        return startups
        
    except Exception as e:
        print(f"Error fetching from HackerNews: {e}")
        return []

# --- DATA PROCESSING & UPLOADING ---

def filter_startups(startup_list, keywords):
    """
    Filters a list of startups if their title or description
    contains any of the keywords.
    """
    filtered = []
    keyword_set = set(k.lower() for k in keywords)
    
    for startup in startup_list:
        content_to_check = (startup['title'] + " " + startup['description']).lower()
        
        if any(keyword in content_to_check for keyword in keyword_set):
            filtered.append(startup)
            
    print(f"Filtered down to {len(filtered)} relevant startups based on keywords.")
    return filtered

def add_to_sheet(worksheet, startups, existing_links):
    """
    Formats the startup data and appends it to the Google Sheet,
    avoiding duplicates.
    """
    new_startups = []
    for s in startups:
        if s['link'] not in existing_links:
            new_startups.append(s)
            
    if not new_startups:
        print("No new startups to add to the sheet.")
        return

    print(f"Adding {len(new_startups)} new startups to Google Sheet...")
    
    # Format data for the sheet
    today_str = datetime.now().strftime("%Y-%m-%d")
    rows_to_add = []
    for s in new_startups:
        rows_to_add.append([
            s['source'],
            s['title'],
            s['description'][:500],  # Truncate description
            s['link'],
            today_str,
            s['published_date']
        ])
    
    try:
        # Append all rows in one batch
        worksheet.append_rows(rows_to_add, value_input_option='USER_ENTERED')
        print(f"Successfully added {len(new_startups)} startups.")
    except Exception as e:
        print(f"Error adding rows to Google Sheet: {e}")
        # This can happen due to API rate limits
        if '429' in str(e):
            print("Hit API rate limit. Sleeping for 60 seconds...")
            time.sleep(60)
            # Try one more time
            try:
                worksheet.append_rows(rows_to_add, value_input_option='USER_ENTERED')
                print(f"Successfully added {len(new_startups)} startups after retry.")
            except Exception as e2:
                print(f"Failed to add rows on retry: {e2}")

# --- MAIN EXECUTION ---

def main():
    print("Starting VC Deal Flow Bot...")
    
    # 1. Connect to Google Sheets
    worksheet = setup_google_sheets()
    if not worksheet:
        return  # Stop if connection failed
        
    existing_links = get_existing_links(worksheet)
    print(f"Found {len(existing_links)} existing links in the sheet.")
    
    # 2. Fetch data from all sources
    all_startups = []
    all_startups.extend(fetch_hackernews_launches())
    all_startups.extend(fetch_rss_feed(TECHCRUNCH_RSS_URL, "TechCrunch"))
    all_startups.extend(fetch_rss_feed(YCOMBINATOR_LAUNCHED_RSS_URL, "YCombinator"))
    
    print(f"Found {len(all_startups)} total startups from all sources.")
    
    # 3. Filter for relevant startups
    filtered_startups = filter_startups(all_startups, FILTER_KEYWORDS)
    
    # 4. Add new, relevant startups to the sheet
    add_to_sheet(worksheet, filtered_startups, existing_links)
    
    print("VC Deal Flow Bot finished successfully.")

if __name__ == "__main__":
    main()

