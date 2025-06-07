import os
import re
import requests
from bs4 import BeautifulSoup

KTEL_INDEX_URL = "https://ktelparou.gr/en/index.html"
KNOWLEDGE_FILE = "knowledge_test.txt"  # Update this if needed

def fetch_html(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None

def extract_general_bus_info(soup):
    """Extract relevant paragraphs that mention bus-related keywords."""
    content = []
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if len(text) > 60 and any(keyword in text.lower() for keyword in ["route", "bus", "station", "schedule", "service", "transport"]):
            content.append(text)

    # ✅ Add the referral to the official site here:
    content.append("For full, up-to-date bus schedules and departure times, visit the official site: https://ktelparou.gr/en")
    return content[:8]  # Limit to 8 relevant lines

def build_basic_bus_info():
    soup = fetch_html(KTEL_INDEX_URL)
    if not soup:
        return "## Bus Information (KTEL Paros)\nCould not fetch KTEL index page."

    info_lines = ["## Bus Information (KTEL Paros)", f"Source: {KTEL_INDEX_URL}", ""]
    info_lines += extract_general_bus_info(soup)
    return "\n".join(info_lines)

def update_knowledge_file_basic_summary():
    """Replace everything after '## Bus Information (KTEL Paros)' with fresh summary."""
    new_section = build_basic_bus_info()

    if not os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            f.write(new_section)
        print("[INFO] Created new knowledge file with basic KTEL info.")
        return

    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "## Bus Information (KTEL Paros)"
    if marker in content:
        before = content.split(marker)[0].rstrip()
        content = f"{before}\n{new_section}"
    else:
        content += "\n\n" + new_section

    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("[INFO] knowledge_test.txt updated with basic summary.")
