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


# Fetch the page
url = "https://saka46.fun/nogi/mv/"
response = requests.get(url)
response.raise_for_status()
response.encoding = response.apparent_encoding

# Parse HTML
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

# Sort by yesterday's views descending, top 20
top_20_yesterday = sorted(videos, key=lambda x: x["yesterday_views"], reverse=True)[:20]
top_20_total = sorted(videos, key=lambda x: x["total_views"], reverse=True)[:20]

for list_item in (top_20_yesterday, top_20_total):

    # Find the maximum width needed for the formatted numbers (for perfect alignment)
    max_yesterday = max(video["yesterday_views"] for video in list_item)
    max_total = max(video["total_views"] for video in list_item)

    width_yesterday = len(format_japanese_style(max_yesterday))
    width_total = len(format_japanese_style(max_total))

    print("Top 20 Nogizaka46 MVs by views gained yesterday:")
    print("=" * 80)

    result = ""

    for i, video in enumerate(list_item, 1):
        yesterday_str = format_japanese_style(video["yesterday_views"])
        total_str = format_japanese_style(video["total_views"])

        result += f"{i:2}. {video['title']}\n"
        result += f"昨: {yesterday_str:>{width_total}}\n"
        result += f"合: {total_str:>{width_total}}\n"

        result += "\n"

        print(result)

    result = "```" + result + "```"

    import time
    import os

    TELEGRAM_BOT_TOKEN = os.environ["bot_token"]
    TELEGRAM_CHAT_ID = "-1002350782955"  # os.environ["chat_id"]


    def send_telegram_message(msg, channel_id):
        max_retries = 5
        MAX_LENGTH = 3000

        def send_part(part):
            attempt = 0
            while attempt < max_retries:
                try:
                    payload = {
                        "message_thread_id": "2030",
                        "chat_id": "-1002646331785",  # "chat_id": "-1002350782955",
                        "text": part,
                        "link_preview_options": {"is_disabled": True},
                        "parse_mode": "MarkdownV2",
                    }
                    response = requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        json=payload,
                    )
                    response_json = response.json()
                    if response.ok:
                        print(response_json)
                        time.sleep(2)
                        return
                    else:
                        raise Exception(response_json.get("description", "Unknown error"))
                except Exception as error:
                    print(f"Error: {error}")

                attempt += 1
                print(f"Retrying... ({attempt}/{max_retries})")
                time.sleep(20)

        # Split by \n and accumulate parts <= MAX_LENGTH
        parts = msg.split("\n")
        current_part = ""
        for part in parts:
            if len(current_part) + len(part) + 1 > MAX_LENGTH:
                send_part(current_part)
                current_part = ""
            current_part += ("" if not current_part else "\n") + part

        if current_part:
            send_part(current_part)


    send_telegram_message(result, TELEGRAM_CHAT_ID)
