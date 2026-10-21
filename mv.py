import json
import os
import time
import requests
from bs4 import BeautifulSoup


# Format number in Japanese style: groups of 4 digits separated by space (e.g. 12345678 → 1234 5678)
def format_japanese_style(number):
    s = f"{number:,}".replace(",", "")
    groups = []
    while s:
        groups.append(s[-4:])
        s = s[:-4]
    return " ".join(reversed(groups)).strip()


# Telegram JSON document sender function
def send_telegram_document(data, caption, channel_id):
    TELEGRAM_BOT_TOKEN = os.environ.get("bot_token")
    max_retries = 5
    attempt = 0
    last_error = None
    while attempt < max_retries:
        try:
            payload = {
                
                "chat_id": channel_id,
                "caption": caption,
            }
            if channel_id.startswith("-1002646331785"):
                payload["message_thread_id"] = "2030"
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                data=payload,
                files={
                    "document": (
                        "mv_rankings.json",
                        json.dumps(data, ensure_ascii=False, indent=2),
                        "application/json",
                    )
                },
            )
            response_json = response.json()
            if response.ok:
                print(response_json)
                time.sleep(2)
                return
            raise RuntimeError(response_json.get("description", "Unknown error"))
        except (requests.RequestException, ValueError, RuntimeError) as error:
            last_error = error
            print(f"Error: {error}")

        attempt += 1
        print(f"Retrying... ({attempt}/{max_retries})")
        if attempt < max_retries:
            time.sleep(20)

    raise RuntimeError(
        f"Failed to send rankings after {max_retries} attempts"
    ) from last_error


# -------------------------------------------------------------
# Fetch and Parse Data
# -------------------------------------------------------------
url = "https://saka46.fun/nogi/mv/"
response = requests.get(url)
response.raise_for_status()
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table")
if not table:
    raise ValueError("Table not found on the page")

rows = table.find_all("tr")
videos = []

for row in rows:
    cols = row.find_all("td")
    if len(cols) < 4:
        continue

    rank = cols[0].get_text(strip=True)
    title_cell = cols[1]
    title_links = title_cell.find_all("a")
    title = (
        title_links[0].get_text(strip=True)
        if title_links
        else title_cell.get_text(strip=True)
    )

    total_views_str = cols[2].get_text(strip=True).replace(",", "")
    total_views = int(total_views_str) * 10000

    yesterday_views_str = cols[3].get_text(strip=True).replace(",", "")
    yesterday_views = int(yesterday_views_str)

    videos.append(
        {
            "rank": rank,
            "title": title,
            "total_views": total_views,
            "yesterday_views": yesterday_views,
        }
    )

# Sort rankings
top_20_yesterday = sorted(videos, key=lambda x: x["yesterday_views"], reverse=True)[:20]
top_20_total = sorted(videos, key=lambda x: x["total_views"], reverse=True)[:20]

# Find target song for the document caption.
target_song = "バンドエイド剥がすような別れ方"
matched_video = next(
    (video for video in videos if target_song in video["title"]), None
)

if matched_video:
    yesterday_str = (matched_video["yesterday_views"])
    total_str = (matched_video["total_views"])
    yesterday_rank = next(
        rank
        for rank, video in enumerate(
            sorted(videos, key=lambda x: x["yesterday_views"], reverse=True), 1
        )
        if video is matched_video
    )

    caption = (
        f"{matched_video['title']}\n"
        f"昨順位: {yesterday_rank}位\n"
        f"昨: {yesterday_str}\n"
        f"合: {int(total_str)/10000:.0f}万"
    )

    ranking_data = {
        "videos": videos,
        "top_20_yesterday": top_20_yesterday,
        "top_20_total": top_20_total,
        "target_song": {
            **matched_video,
            "yesterday_rank": yesterday_rank,
        },
    }
    print("Sending rankings as one JSON document:")
    print(caption)
    send_telegram_document(ranking_data, caption, "-1002646331785")
    send_telegram_document(ranking_data, caption, "-1002350782955")
else:
    print(f"Target song '{target_song}' was not found in the parsed data.")
