import io
import json
import os

import streamlit as st
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_FILE = os.environ.get("GDRIVE_TOKEN_FILE", "secrets/token.json")
STATE_FILE_NAME = "tracker_state.json"


class GDriveNotConfigured(Exception):
    pass


def _cloud_secrets():
    try:
        section = st.secrets.get("gdrive")
        return dict(section) if section else None
    except Exception:
        return None


def _folder_id():
    cloud = _cloud_secrets()
    if cloud and cloud.get("folder_id"):
        return cloud["folder_id"]
    return os.environ.get("GDRIVE_FOLDER_ID")


def _token_info():
    cloud = _cloud_secrets()
    if cloud and cloud.get("token_json"):
        return json.loads(cloud["token_json"])
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


def is_configured():
    return bool(_folder_id() and _token_info())


def get_service():
    if not is_configured():
        raise GDriveNotConfigured(
            "Не найден ID папки или токен Google. Локально: python gdrive_auth.py, "
            "в облаке: секцию [gdrive] в Secrets."
        )
    creds = Credentials.from_authorized_user_info(_token_info(), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        if not _cloud_secrets():
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _find_file_id(service, name, parent_id):
    query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    result = service.files().list(q=query, fields="files(id, name)").execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None


def load_state():
    service = get_service()
    file_id = _find_file_id(service, STATE_FILE_NAME, _folder_id())
    if not file_id:
        return None
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return json.loads(buf.getvalue().decode("utf-8"))


def save_state(state):
    service = get_service()
    payload = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(payload), mimetype="application/json", resumable=False)
    file_id = _find_file_id(service, STATE_FILE_NAME, _folder_id())
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": STATE_FILE_NAME, "parents": [_folder_id()]}
        service.files().create(body=metadata, media_body=media, fields="id").execute()


def upload_document(name, data, mimetype="application/octet-stream"):
    service = get_service()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mimetype, resumable=False)
    metadata = {"name": name, "parents": [_folder_id()]}
    file = service.files().create(
        body=metadata, media_body=media, fields="id, webViewLink"
    ).execute()
    return file["id"], file.get("webViewLink")


def delete_document(file_id):
    service = get_service()
    service.files().delete(fileId=file_id).execute()
