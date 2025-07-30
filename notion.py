from notion_client import Client
from dotenv import load_dotenv
from Helper import get_summary_fromAI
import os
import time

load_dotenv()

NOTION_KEY = os.getenv("NOTION_API_KEY")
DB_KEY = os.getenv("DB_KEY")

notion = Client(auth=NOTION_KEY)


def extract_text_from_rich_text(rich_text_array):
    return ''.join(rt.get("plain_text", "") for rt in rich_text_array)


def fetch_block_content(block_id):
    """Recursively collect text from a block and its descendants, with pagination."""
    text_content = []
    cursor = None

    while True:
        resp = notion.blocks.children.list(block_id, start_cursor=cursor, page_size=100)
        for block in resp.get("results", []):
            block_type = block.get("type")

            if block_type in {
                "paragraph", "heading_1", "heading_2", "heading_3",
                "bulleted_list_item", "numbered_list_item", "to_do", "quote", "callout"
            }:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                content = extract_text_from_rich_text(rich_text)
                if content.strip():
                    text_content.append(content)

            # recurse if this block has children
            if block.get("has_children"):
                text_content.extend(fetch_block_content(block["id"]))

        if resp.get("has_more"):
            cursor = resp["next_cursor"]
        else:
            break

    return text_content


def crawl_database(database_id):
    """Iterate pages in DB (with pagination), summarize each, collect all results."""
    all_notes = []
    cursor = None

    while True:
        response = notion.databases.query(database_id=database_id, start_cursor=cursor, page_size=100)

        for page in response["results"]:
            page_id = page["id"]
            print(page_id)

            # 1) Fetch content as list of strings
            parts = fetch_block_content(page_id)

            # 2) Join to a single string for the LLM
            text = "\n".join(parts).strip()
            if not text:
                print("[warn] Page has no text; skipping.")
                continue

            # 3) Summarize (ensure get_summary_fromAI returns a str)
            try:
                phrase = get_summary_fromAI(text)
            except Exception as e:
                print(f"[warn] LLM failed on {page_id}: {e}")
                continue

            if not phrase or not isinstance(phrase, str) or not phrase.strip():
                print(f"[warn] Empty summary for {page_id}; skipping.")
                continue

            # Optional: normalize newlines for consistent line counts
            phrase = phrase.replace("\r\n", "\n").replace("\r", "\n").strip()

            # Keep in memory for now; we’ll write once at the end
            all_notes.append(phrase)

            # (Optional) polite rate-limiting to avoid API throttling
            time.sleep(0.1)

        if response.get("has_more"):
            cursor = response["next_cursor"]
        else:
            break

    return all_notes


def save_notes(notes, path="DATA/nottest.txt"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        for i, note in enumerate(notes, 1):
            f.write(f"--- NOTE {i} ---\n")
            f.write(note.rstrip() + "\n\n")
    print(f"[✓] Wrote {len(notes)} summaries to {path}")


if __name__ == "__main__":
    database_id = DB_KEY
    all_text = crawl_database(database_id)
    save_notes(all_text)
