import requests


def send_discord_message(message: str, webhook_url: str) -> None:
    if not webhook_url:
        return

    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code not in (200, 204):
            print(f"Failed to send Discord message: {response.status_code} {response.text}")
    except Exception as exc:
        print(f"Error sending Discord message: {exc}")
