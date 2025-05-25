#!/bin/bash
# Bash script to auto-ingest documentation into the backend after startup

# You can add more URLs to this list as needed
DOC_URLS=(
  "https://docs.python.org/3/"
  # Add more documentation URLs here
)

BACKEND_URL="http://localhost:8000/ingest_documentation"

for url in "${DOC_URLS[@]}"; do
  echo "[Auto-Ingest] Sending ingestion request for $url..."
  curl -X POST "$BACKEND_URL" \
    -H "Content-Type: application/json" \
    -d '{"url": "'$url'", "crawl_limit": 10}'
  echo -e "\n[Auto-Ingest] Done with $url.\n"
done

echo "All ingestion requests sent. Check backend logs for progress/results."
