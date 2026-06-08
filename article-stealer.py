import html
import re
import subprocess
import sys
from pathlib import Path

import cloudscraper
import trafilatura
from playwright.sync_api import sync_playwright


def paragraphs(text):
    parts = re.split(r"\n\s*\n|\n", text)
    return [p.strip() for p in parts if len(p.strip()) > 40]


def build_html(url, text, title="Clean Text View"):
    body = "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs(text))

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      background: #f4f1ea;
      color: #171717;
      font-family: Georgia, serif;
      line-height: 1.8;
    }}
    .wrap {{
      max-width: 680px;
      margin: 48px auto;
      background: white;
      padding: 48px 56px;
      border-radius: 18px;
      box-shadow: 0 20px 60px rgba(0,0,0,.12);
    }}
    .kicker {{
      font-family: Arial, sans-serif;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: #0b8f87;
      font-size: 12px;
      font-weight: bold;
    }}
    h1 {{
      font-size: 28px;
      margin: 8px 0 12px;
      line-height: 1.3;
    }}
    .url {{
      font-family: Arial, sans-serif;
      font-size: 12px;
      color: #999;
      word-break: break-all;
      margin-bottom: 36px;
    }}
    p {{
      font-size: 17px;
      margin: 0 0 20px;
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <div class="kicker">Scraped Article Preview</div>
    <h1>{html.escape(title)}</h1>
    <div class="url">{html.escape(url)}</div>
    {body}
  </main>
</body>
</html>"""


def main():
    url = input("Enter URL: ").strip()

    if not url.startswith(("http://", "https://")):
        print("Please enter a full URL starting with https://")
        return

    scraper = cloudscraper.create_scraper()

    try:
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch URL: {e}")
        return

    raw_html = response.text
    metadata = trafilatura.extract_metadata(raw_html)
    text = trafilatura.extract(raw_html)

    if not text:
        print("No article text found.")
        return

    title = (metadata.title if metadata and metadata.title else "article")
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()
    safe_title = re.sub(r'\s+', '-', safe_title).lower()[:80]

    out_dir = Path("scraped_preview")
    out_dir.mkdir(exist_ok=True)

    pdf_file = out_dir / f"{safe_title}.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(build_html(url, text, title))
        page.pdf(
            path=str(pdf_file),
            format="Letter",
            margin={"top": "40px", "right": "40px", "bottom": "40px", "left": "40px"}
        )
        browser.close()

    print(f"\nSaved to: {pdf_file}")

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(pdf_file)])


if __name__ == "__main__":
    main()
