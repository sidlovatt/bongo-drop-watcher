"""Watch bongospares.co.uk/shop and push a phone alert (via ntfy) when a product
is added or put on sale. State is kept in seen.json, committed back by the workflow."""
import json
import os
import sys
import urllib.request

SHOP = "https://bongospares.co.uk"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen.json")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (bongo-drop-watcher)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_products():
    products, url = [], f"{SHOP}/shop?format=json"
    while url:
        page = get_json(url)
        products += page.get("items", [])
        nxt = page.get("pagination", {})
        url = f"{SHOP}{nxt['nextPageUrl']}&format=json" if nxt.get("nextPage") else None
    return products


def price_text(item):
    v = (item.get("variants") or [{}])[0]
    price = v.get("priceMoney", {}).get("value")
    if v.get("onSale"):
        sale = v.get("salePriceMoney", {}).get("value")
        return f"£{sale} (was £{price})"
    return f"£{price}" if price else ""


def in_stock(item):
    v = (item.get("variants") or [{}])[0]
    return v.get("unlimited") or v.get("qtyInStock", 0) > 0


def notify(title, item):
    msg = f"{item['title']}\n{price_text(item)}"
    if not in_stock(item):
        msg += "\n(showing out of stock)"
    payload = {
        "topic": NTFY_TOPIC,
        "title": title,
        "message": msg,
        "click": SHOP + item["fullUrl"],
        "tags": ["red_car"],
        "priority": 5,
    }
    if item.get("assetUrl"):
        payload["attach"] = item["assetUrl"] + "?format=500w"
    if not NTFY_TOPIC:
        print("[dry run]", json.dumps(payload, ensure_ascii=False))
        return
    req = urllib.request.Request(
        "https://ntfy.sh/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=30)
    print("Notified:", title, "-", item["title"])


def main():
    products = fetch_products()
    current = {p["id"]: bool((p.get("variants") or [{}])[0].get("onSale")) for p in products}

    if not os.path.exists(STATE_FILE):
        # First run: remember everything without alerting
        json.dump(current, open(STATE_FILE, "w"), indent=0, sort_keys=True)
        print(f"First run: recorded {len(current)} products, no alerts sent.")
        return

    seen = json.load(open(STATE_FILE))
    alerts = 0
    for p in products:
        pid = p["id"]
        if pid not in seen:
            notify("New on Bongo Spares!", p)
            alerts += 1
        elif current[pid] and not seen[pid]:
            notify("Now on SALE at Bongo Spares!", p)
            alerts += 1
    print(f"Checked {len(products)} products, {alerts} alert(s) sent.")

    # Keep ids of products that vanished, so a relisting isn't re-alerted as new
    seen.update(current)
    json.dump(seen, open(STATE_FILE, "w"), indent=0, sort_keys=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a blip on the shop's side shouldn't fail the run noisily
        print("Check failed:", e, file=sys.stderr)
