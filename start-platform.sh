#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — show current live URL and test connectivity

URL_FILE="$HOME/platform-x/logs/tunnel.url"

echo "=== Platform-X Status ==="
sv status platform-x-api 2>&1
sv status platform-x-tunnel 2>&1
echo ""

if [ -f "$URL_FILE" ]; then
  URL=$(cat "$URL_FILE")
  echo "Live URL: $URL"
  echo ""
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null)
  echo "HTTP check: $CODE"
  if [ "$CODE" = "200" ]; then
    echo "✅ Site is online"
  else
    echo "⏳ Tunnel warming up or down — wait 15s and try again"
  fi
else
  echo "No URL file yet"
fi
