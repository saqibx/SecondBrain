from notion_client import Client
from dotenv import load_dotenv
import os
load_dotenv()

NOTION_KEY = os.getenv("NOTION_API_KEY")
DB_KEY = os.getenv("DB_KEY")

notion = Client(auth=NOTION_KEY)

def extract_text_from_rich_text(rich_text_array):
    return ''.join([rt.get("plain_text", "") for rt in rich_text_array])

def fetch_block_content(block_id):
    text_content = []
    children = notion.blocks.children.list(block_id)

    for block in children.get("results", []):
        block_type = block.get("type")

        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
            rich_text = block.get(block_type, {}).get("rich_text", [])
            content = extract_text_from_rich_text(rich_text)
            if content.strip():
                text_content.append(content)

        if block.get("has_children"):
            text_content.extend(fetch_block_content(block["id"]))

    return text_content

def crawl_database(database_id):
    all_notes = []
    cursor = None

    while True:
        response = notion.databases.query(database_id=database_id, start_cursor=cursor)

        for page in response["results"]:
            all_notes.append(f"--- Page: {page['id']} ---")
            all_notes.extend(fetch_block_content(page["id"]))

        if response.get("has_more"):
            cursor = response["next_cursor"]
        else:
            break

    return all_notes


database_id = DB_KEY
all_text = crawl_database(database_id)


with open("DATA/notion_output.txt", "w", encoding="utf-8") as f:
    for line in all_text:
        f.write(line + "\n")
