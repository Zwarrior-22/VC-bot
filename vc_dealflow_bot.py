import requests
import feedparser
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound, APIError
from datetime import datetime
import time

# --- CONFIGURATION ---

# --- Main Setup ---
GOOGLE_SHEET_ID = "1X1bVNsZJLB9hHX-l7T0hLrb4d_R3BCJyfeJAtpDComk" #enter your sheet id
SERVICE_ACCOUNT_FILE = 'credentials.json'

# --- Investment Theses (Worksheet Name: [Keywords]) ---
# Startups are added to the *first* thesis they match.
THESES = {
    "AI & ML": [
        'ai agent', 'llm', 'generative ai', 'genai', 'rag', 
        'computer vision', 'ai safety', 'mlops'
    ],
    "Future of Data": [
        'data infrastructure', 'platform engineering', 'observability', 
        'data pipeline', 'cloud native', 'serverless'
    ],
    "Developer Tools": [
        'devops', 'developer tool', 'api', 'open-source', 'wasm', 
        'kubernetes', 'cybersecurity'
    ],
    "General B2B": [
        'ai', 'ml', 'saas', 'b2b', 'fintech', 'plg', 'workflow automation'
    ]
}

# --- Data Sources ---
TECHCRUNCH_RSS_URL = 'https://techcrunch.com/feed/'
YCOMBINATOR_LAUNCHED_RSS_URL = 'https://www.ycombinator.com/blog/launched/rss'
HACKERNEWS_LAUNCH_HN_API = "http://hn.algolia.com/api/v1/search_by_date?query=Launch%20HN&tags=story"
VENTUREBEAT_RSS_URL = 'https://venturebeat.com/feed/'

# --- GOOGLE SHEETS SETUP ---

def setup_google_sheets(sheet_id, theses_config):
    """
    Connects to Google Sheets, opens the spreadsheet, and ensures
    a worksheet exists for every defined thesis.
    Returns a dictionary of worksheet objects.
    """
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(sheet_id)
        
        worksheets = {}
        header = ['Source', 'Company/Title', 'Description', 'Link', 'Date Found', 'Published Date']
        
        for worksheet_name in theses_config.keys():
            try:
                worksheet = sheet.worksheet(worksheet_name)
                print(f"Found worksheet: '{worksheet_name}'")
            except WorksheetNotFound:
                print(f"Worksheet '{worksheet_name}' not found. Creating it...")
                worksheet = sheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
                worksheet.append_row(header)
                print(f"Worksheet '{worksheet_name}' created and header row added.")
            worksheets[worksheet_name] = worksheet
            
        print("\nAll worksheets are ready.")
        return worksheets
        
    except APIError as e:
        print("\n--- ERROR: API ERROR ---")
        if "PERMISSION_DENIED" in str(e):
             print("PERMISSION_DENIED: The service account is not an 'Editor' on the Google Sheet.")
             print("Please double-check your 'Share' settings on the Google Sheet.")
        elif "NOT_FOUND" in str(e) or "Spreadsheet not found" in str(e):
             print(f"NOT_FOUND: The Google Sheet with ID '{sheet_id}' was not found.")
             print("Please double-check that your GOOGLE_SHEET_ID is correct.")
        else:
             print(f"An API error occurred: {e}")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please ensure 'credentials.json' and 'GOOGLE_SHEET_ID' are correct.")
        return None

def get_existing_links(worksheets_dict):
    """
    Fetches all links from all thesis worksheets to avoid duplicates.
    """
    existing_links = set()
    print("Fetching existing links from all worksheets to prevent duplicates...")
    try:
        for worksheet_name, worksheet in worksheets_dict.items():
            links = worksheet.col_values(4)  # 4th column is 'Link'
            existing_links.update(links)
        print(f"Found {len(existing_links)} total unique links across all sheets.")
        return existing_links
    except Exception as e:
        print(f"Warning: Could not fetch existing links. May create duplicates. Error: {e}")
        return set()

# --- DATA FETCHING ---

def fetch_rss_feed(url, source_name):
    """
    A generic function to fetch and parse an RSS feed.
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
    """
    print("Fetching from HackerNews 'Launch HN'...")
    startups = []
    try:
        response = requests.get(HACKERNEWS_LAUNCH_HN_API)
        response.raise_for_status()
        hits = response.json().get('hits', [])
        
        for hit in hits:
            title = hit.get('title', 'No Title')
            link = hit.get('story_url') or f"https://news.ycombinator.com/item?id={hit['objectID']}"
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

def categorize_startups(startup_list, theses_config):
    """
    Categorizes startups based on the defined theses.
    A startup is assigned to the *first* thesis it matches.
    """
    print("Categorizing startups based on your theses...")
    categorized_startups = {thesis_name: [] for thesis_name in theses_config.keys()}
    
    # Pre-compile keyword sets for efficiency
    theses_keywords = {
        name: set(k.lower() for k in keywords) 
        for name, keywords in theses_config.items()
    }
    
    for startup in startup_list:
        content_to_check = (startup['title'] + " " + startup['description']).lower()
        
        for thesis_name, keywords in theses_keywords.items():
            if any(keyword in content_to_check for keyword in keywords):
                categorized_startups[thesis_name].append(startup)
                break  # Stop at the first match
            
    print("Categorization complete.")
    for thesis_name, startups in categorized_startups.items():
        print(f"  - Found {len(startups)} startups for '{thesis_name}' thesis.")
        
    return categorized_startups

def add_startups_to_sheets(worksheets_dict, categorized_startups, existing_links):
    """
Update the `add_startups_to_sheets` function in `vc_dealflow_bot.py` to truncate the description to 500 characters, handle `None` descriptions gracefully, and ensure all dates are formatted as strings before appending to the sheet.
    """
    print("\nAdding new startups to Google Sheet...")
    total_added = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for worksheet_name, startups_to_add in categorized_startups.items():
        if not startups_to_add:
            continue
            
        worksheet = worksheets_dict[worksheet_name]
        new_rows_data = []
        
        for s in startups_to_add:
            if s['link'] not in existing_links:
                
                # Ensure description is a string and truncate
                description = s.get('description') or ""
                if not isinstance(description, str):
                    description = str(description)
                description = description[:500]

                # Ensure published_date is a string
                published_date = s.get('published_date') or "N/A"
                if not isinstance(published_date, str):
                    published_date = str(published_date)

                new_rows_data.append([
                    s['source'],
                    s['title'],
                    description,
                    s['link'],
                    today_str,
                    published_date
                ])
                existing_links.add(s['link']) # Add to set to prevent duplicates in same run
        
        if not new_rows_data:
            print(f"No new startups to add to '{worksheet_name}'.")
            continue
            
        print(f"Adding {len(new_rows_data)} new startups to '{worksheet_name}'...")
        total_added += len(new_rows_data)
        
        try:
            worksheet.append_rows(new_rows_data, value_input_option='USER_ENTERED')
            print(f"Successfully added {len(new_rows_data)} startups to '{worksheet_name}'.")
        except Exception as e:
            print(f"Error adding rows to '{worksheet_name}': {e}")
            if '429' in str(e):
                print("Hit API rate limit. Sleeping for 60 seconds...")
                time.sleep(60)
                try:
                    worksheet.append_rows(new_rows_data, value_input_option='USER_ENTERED')
                    print(f"Successfully added {len(new_rows_data)} startups after retry.")
                except Exception as e2:
                    print(f"Failed to add rows on retry: {e2}")
                    
    print(f"\nAdded a total of {total_added} new startups across all theses.")

# --- MAIN EXECUTION ---

def main():
    print("Starting Thesis-Driven VC Deal Flow Bot...")
    
    # 1. Connect to Google Sheets and set up all worksheets
    worksheets_dict = setup_google_sheets(GOOGLE_SHEET_ID, THESES)
    if not worksheets_dict:
        return  # Stop if connection failed
        
    # 2. Get all existing links to prevent duplicates
    existing_links = get_existing_links(worksheets_dict)
    
    # 3. Fetch data from all sources
    all_startups = []
    all_startups.extend(fetch_hackernews_launches())
    all_startups.extend(fetch_rss_feed(TECHCRUNCH_RSS_URL, "TechCrunch"))
    all_startups.extend(fetch_rss_feed(YCOMBINATOR_LAUNCHED_RSS_URL, "YCombinator"))
    all_startups.extend(fetch_rss_feed(VENTUREBEAT_RSS_URL, "VentureBeat"))
    print(f"\nFound {len(all_startups)} total startups from all sources.")
    
    # 4. Categorize startups based on defined theses
    categorized_startups = categorize_startups(all_startups, THESES)
    
    # 5. Add new, relevant startups to their corresponding sheets
    add_startups_to_sheets(worksheets_dict, categorized_startups, existing_links)
    
    print("\nVC Deal Flow Bot finished successfully.")

if __name__ == "__main__":
    main()

