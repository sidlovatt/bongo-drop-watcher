# Bongo drop watcher

Checks https://bongospares.co.uk/shop every 5 minutes during the day and sends a
phone notification (via the free ntfy app) when a product is added or put on sale.

- `watch.py` – the checker
- `seen.json` – products already seen (updated automatically)
- Secret `NTFY_TOPIC` – the ntfy topic your phone is subscribed to
