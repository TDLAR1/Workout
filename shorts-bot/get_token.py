"""One-time setup: run this on your own computer to get YT_REFRESH_TOKEN.

    pip install google-auth-oauthlib
    python get_token.py path/to/client_secret.json

A browser opens; sign in with the Google account that owns your channel.
"""

import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

secret_file = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
creds = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES).run_local_server(
    port=0, access_type="offline", prompt="consent"
)
client = json.load(open(secret_file))["installed"]

print("\nAdd these three as GitHub repository secrets:\n")
print("YT_CLIENT_ID     =", client["client_id"])
print("YT_CLIENT_SECRET =", client["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
