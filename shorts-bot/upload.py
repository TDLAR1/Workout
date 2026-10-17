"""Upload out/short.mp4 to YouTube, then mark its script as posted.

Needs three environment variables (stored as GitHub secrets):
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (see get_token.py)
Optional:
    YT_PRIVACY = public | unlisted | private   (default: public)
"""

import json
import os
from pathlib import Path

import requests

HERE = Path(__file__).parent
OUT = HERE / "out"
POSTED = HERE / "state" / "posted.json"

EDUCATION_CATEGORY = "27"


def access_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["YT_CLIENT_ID"],
            "client_secret": os.environ["YT_CLIENT_SECRET"],
            "refresh_token": os.environ["YT_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def upload(video, meta, token):
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": EDUCATION_CATEGORY,
        },
        "status": {
            "privacyStatus": os.environ.get("YT_PRIVACY", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    # Resumable upload: first create the session, then send the file.
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(video.stat().st_size),
        },
        json=body,
        timeout=60,
    )
    r.raise_for_status()
    with open(video, "rb") as f:
        r = requests.put(
            r.headers["Location"],
            headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"},
            data=f,
            timeout=600,
        )
    r.raise_for_status()
    return r.json()


def main():
    meta = json.loads((OUT / "meta.json").read_text())
    result = upload(OUT / "short.mp4", meta, access_token())
    print(f"Uploaded: https://youtube.com/shorts/{result['id']} "
          f"({result['status']['privacyStatus']})")

    posted = json.loads(POSTED.read_text()) if POSTED.exists() else []
    posted.append(meta["id"])
    POSTED.parent.mkdir(exist_ok=True)
    POSTED.write_text(json.dumps(posted, indent=2) + "\n")


if __name__ == "__main__":
    main()
