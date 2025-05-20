import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import os
import time
import re
from PIL import Image, ImageDraw, ImageFont
import textwrap

# === SETTINGS ===
LIST_URL = "https://security.berkeley.edu/resources/phish-tank?sort_by=created&sort_order=DESC&topics=Phishing&topics_op=or&type%5Bopenberkeley_news_item%5D=openberkeley_news_item&type_op=in&page=6"
BASE_URL = "https://security.berkeley.edu"
IMG_DIR = "phishing_images"
TXT_DIR = "phishing_texts"

# === SETUP ===
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(TXT_DIR, exist_ok=True)

# === FUNCTION: Convert text to image ===
def save_text_as_image(text: str, output_path: str, width=800, font_size=16):
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
    except:
        font = ImageFont.load_default()

    lines = text.splitlines()
    bbox = font.getbbox("A")
    line_height = bbox[3] - bbox[1] + 6
    img_height = line_height * len(lines) + 20
    max_line_length = max([font.getlength(line) for line in lines]) if lines else 0
    img_width = max(int(max_line_length + 20), width)

    img = Image.new("RGB", (img_width, img_height), color="white")
    draw = ImageDraw.Draw(img)

    y = 10
    for line in lines:
        draw.text((10, y), line, font=font, fill="black")
        y += line_height

    img.save(output_path)

# === STEP 1: Scrape listing page ===
resp = requests.get(LIST_URL)
soup = BeautifulSoup(resp.content, 'html.parser')
example_links = soup.select('a[href^="/news/"]')
visited = set()

for link in example_links:
    href = link['href']
    full_url = urljoin(BASE_URL, href)
    if full_url in visited:
        continue
    visited.add(full_url)

    print(f"Processing: {full_url}")
    try:
        example_resp = requests.get(full_url)
        example_soup = BeautifulSoup(example_resp.content, 'html.parser')

        safe_name = re.sub(r'[^\w\-_.]', '_', href.strip('/'))

        # === Process images (non-SVG only) ===
        # 1. Collect all <img> tags INSIDE the phishing message block
        phishing_imgs = set()
        original_msg_header = example_soup.find(lambda tag: tag.name in ["h3", "h4"] and "Original Message" in tag.text)
        if original_msg_header:
            # Extract any <img> directly under <p> after Original Message (treat as visual example)
            img_in_message = []
            node = original_msg_header.find_next_sibling()
            while node and isinstance(node, Tag):
                if node.name and node.name.startswith("h"):
                    break

                # ✅ If it's a <p> and directly contains <img>, keep those
                if node.name == "p":
                    for img in node.find_all("img", recursive=False):
                        img_in_message.append(img)

                node = node.find_next_sibling()


        # 2. Find all images on the page, but exclude those found in phishing content
        imgs = [
            img for img in example_soup.find_all("img")
            if (img not in phishing_imgs or img in img_in_message)
        ]


        for i, img in enumerate(imgs):
            src = img.get("src")
            if not src or src.lower().endswith(".svg"):
                continue
            img_url = urljoin(BASE_URL, src)
            print(f"  -> Image: {img_url}")
            try:
                img_data = requests.get(img_url, timeout=5).content
                img_path = os.path.join(IMG_DIR, f"{safe_name}_{i}.jpg")
                if not os.path.exists(img_path):
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                time.sleep(0.2)
            except Exception as e:
                print(f"  !! Skipped image due to error: {e}")


        # === Extract content following <h3> or <h4> Original Message ===
        original_msg_header = example_soup.find(lambda tag: tag.name in ["h3", "h4"] and "Original Message" in tag.text)
        if original_msg_header:
            lines = []
            node = original_msg_header.find_next_sibling()
            while node and isinstance(node, Tag):
                if node.name and node.name.startswith("h"):
                    break
                if node.name in ["p", "div"]:
                    text = node.get_text(separator="\n", strip=True)
                    if text:
                        lines.append(text)
                elif node.name == "table":
                    # Process only this top-level table — do not recurse into deeper tables inside its cells
                    for td in node.find_all("td", recursive=True):
                        # Skip any td that's inside a nested <table>
                        if td.find_parent("table") != node:
                            continue

                        # Remove any <img> or <table> inside td before extracting text
                        for tag in td.find_all(["img", "table"]):
                            tag.decompose()

                        # Now safely extract spans
                        for span in td.find_all("span"):
                            for br in span.find_all("br"):
                                br.replace_with("\n")
                            text = span.get_text(separator="\n", strip=True).replace("\xa0", " ")
                            if text:
                                lines.append(text)

                        # Also extract from divs
                        for div in td.find_all("div"):
                            for br in div.find_all("br"):
                                br.replace_with("\n")
                            text = div.get_text(separator="\n", strip=True).replace("\xa0", " ")
                            if text:
                                lines.append(text)

                        # And extract from p tags
                        for p in td.find_all("p"):
                            for br in p.find_all("br"):
                                br.replace_with("\n")
                            text = p.get_text(separator="\n", strip=True).replace("\xa0", " ")
                            if text:
                                lines.append(text)






                elif node.name == "pre":
                    text = node.get_text(separator="\n", strip=True)
                    if text:
                        lines.append(text)
                elif node.name == "blockquote":
                    text = node.get_text(separator="\n", strip=True)
                    if text:
                        lines.append(text)
                node = node.find_next_sibling()

            if lines:
                full_text = "\n".join(lines)
                print(f"  -> Found phishing Original Message content")

                txt_path = os.path.join(TXT_DIR, f"{safe_name}_original.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)

                text_img_path = os.path.join(IMG_DIR, f"{safe_name}_original.jpg")
                if not os.path.exists(text_img_path):
                    save_text_as_image(full_text, text_img_path)

    except Exception as e:
        print(f"  !! Failed to process {full_url}: {e}")
