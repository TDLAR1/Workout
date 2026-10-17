# Shorts bot

Posts one personal-finance YouTube Short per day, for free.

Every day, a GitHub Action:

1. picks the next unposted script from `scripts.json` (30 included),
2. reads it aloud with a free Microsoft neural voice (edge-tts),
3. builds a 1080×1920 video with animated captions in ffmpeg,
4. uploads it to your channel and records it in `state/posted.json`.

Cost: $0. The YouTube API and GitHub Actions free tiers are more than enough for one video a day.

## One-time setup (about 20 minutes)

### 1. Make a YouTube channel
Use a Google account you're OK dedicating to this.

### 2. Get YouTube API access (free)
1. Go to <https://console.cloud.google.com/>, then create a new project.
2. **APIs & Services → Library**, search **YouTube Data API v3**, and click **Enable**.
3. **APIs & Services → OAuth consent screen**: choose **External**, fill in the app name and your email, and add yourself as a test user.
4. On the same screen, click **Publish app** ("In production").
   Without this step, your login token expires after 7 days and the bot stops.
5. **APIs & Services → Credentials → Create credentials → OAuth client ID**, choose **Desktop app**, and download the JSON file.

### 3. Get your refresh token (on your own computer)
```bash
pip install google-auth-oauthlib
python get_token.py path/to/the-downloaded-file.json
```
Sign in with your channel's account. Google will warn that the app is unverified: click **Advanced → Go to (app)**. That's fine, because it's your own app.

### 4. Add the secrets to GitHub
Repo → **Settings → Secrets and variables → Actions → New repository secret**. Add the three values it printed:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

### 5. Turn it on
Scheduled workflows only run from the default branch, so merge this into `main`.
Then go to **Actions → Daily YouTube Short → Run workflow** to post the first one right away.

## Things to know

- **Videos may upload as private at first.** YouTube locks uploads from new, unaudited API projects to private.
  Either open YouTube Studio and switch each video to Public (one click), or apply for the free
  [API audit](https://support.google.com/youtube/contact/yt_api_form) to remove the lock.
- **Monetization:** YouTube doesn't pay for "mass-produced or repetitive" content.
  To get approved for the Partner Program, keep scripts varied and useful.
  Your own voice, real footage or a face later on all help a lot.
- **Running out of scripts:** after 30 days the bot stops and says so. Add more entries to `scripts.json`
  (same format), or ask Claude to write another batch.
- Every run keeps the finished video for 7 days under the workflow run's **Artifacts**, so you can repost it to TikTok or Instagram Reels by hand.

## Test locally
```bash
pip install -r requirements.txt   # also needs ffmpeg installed
python make_short.py              # writes out/short.mp4
python make_short.py --silent-test --id rule-of-72   # no voice, video only
```
