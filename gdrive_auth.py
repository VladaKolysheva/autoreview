import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive"]
CLIENT_FILE = os.environ.get("GDRIVE_OAUTH_CLIENT_FILE", "secrets/oauth-client.json")
TOKEN_FILE = os.environ.get("GDRIVE_TOKEN_FILE", "secrets/token.json")

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_FILE, "w", encoding="utf-8") as f:
    f.write(creds.to_json())

print(f"Готово, токен сохранён в {TOKEN_FILE}")
