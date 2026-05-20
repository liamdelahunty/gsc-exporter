
import os
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'

def main():
    parser = argparse.ArgumentParser(description="Authenticate GSC Exporter in Cloud Shell.")
    parser.add_argument("--name", help="Optional name for the token file (e.g., 'work').", default=None)
    args = parser.parse_args()

    token_file = 'token.json'
    if args.name:
        token_file = f"token-{args.name}.json"

    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"Error: {CLIENT_SECRET_FILE} not found. Ensure it is in this directory.")
        return

    # Initialize the flow
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, 
        scopes=SCOPES,
        redirect_uri='http://localhost:8080'
    )
    
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    
    print("\n" + "="*60)
    print(f"GSC AUTHENTICATION HELPER - TARGET: {token_file}")
    print("="*60)
    print("\n1. Open this URL in your browser:\n")
    print(auth_url)
    print("\n2. IMPORTANT: Log into the Google Account you want to use.")
    print("3. Click 'Allow'.")
    print("\n4. Your browser will show 'This site can’t be reached' at localhost:8080.")
    print("\n5. Copy the code from the address bar (text after 'code=')")
    
    code = input("\nEnter the 'code' from the URL: ").strip()
    
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        print("\n" + "="*60)
        print(f"SUCCESS! '{token_file}' has been created.")
        print(f"Run: python interactive-runner.py --token {token_file}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\nError fetching token: {e}")

if __name__ == "__main__":
    main()
