import os, hashlib, requests, datetime
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
PDF_ROOT = "./"
GITHUB_REPO = "https://github.com/Utsab-2010/Research-Materials"
GITHUB_BRANCH = "main"

# Extract database ID from URL if needed
if DATABASE_ID and ('?' in DATABASE_ID or '/' in DATABASE_ID):
    # Extract ID from URL like: https://notion.so/2e6033ce2ca58075ab5ad8ca378bd1af?v=...
    DATABASE_ID = DATABASE_ID.split('/')[-1].split('?')[0].replace('-', '')

notion = Client(auth=NOTION_TOKEN)

def get_existing_pdfs():
    """Get all existing PDF filenames from the database"""
    existing = set()
    try:
        results = notion.databases.query(database_id=DATABASE_ID)
        for page in results.get("results", []):
            title_prop = page["properties"].get("Doc name", {})
            if title_prop.get("title"):
                filename = title_prop["title"][0]["text"]["content"]
                existing.add(filename)
        
        # Handle pagination if there are more results
        while results.get("has_more"):
            results = notion.databases.query(
                database_id=DATABASE_ID,
                start_cursor=results["next_cursor"]
            )
            for page in results.get("results", []):
                title_prop = page["properties"].get("Doc name", {})
                if title_prop.get("title"):
                    filename = title_prop["title"][0]["text"]["content"]
                    existing.add(filename)
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch existing entries: {e}")
    
    return existing

def file_hash(p):
    with open(p,'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def upload_pdf(path, category, existing_pdfs):
    filename = os.path.basename(path)
    
    # Check if already exists
    if filename in existing_pdfs:
        print(f"  ⏭️  Skipping: {filename} (already exists)")
        return False
    
    print(f"  📤 Adding: {filename} (Category: {category})")
    
    # Generate GitHub URL for the PDF
    relative_path = os.path.relpath(path, PDF_ROOT)
    github_url = f"{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{relative_path}"
    
    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Doc name": {"title":[{"text":{"content":filename}}]},
            "Category": {"multi_select":[{"name":category}]}
        },
        children=[
            {
                "object": "block",
                "type": "bookmark",
                "bookmark": {
                    "url": github_url
                }
            }
        ]
    )
    print(f"  ✅ Added to database!")
    print(f"  🔗 GitHub: {github_url}")
    return True

print(f"🔍 Scanning directories in: {os.path.abspath(PDF_ROOT)}\n")

# Get existing PDFs from database
print("📋 Fetching existing entries from Notion...")
existing_pdfs = get_existing_pdfs()
print(f"Found {len(existing_pdfs)} existing entries\n")

total_uploaded = 0
total_skipped = 0
for item in os.listdir(PDF_ROOT):
    folder_path = os.path.join(PDF_ROOT, item)
    if os.path.isdir(folder_path):
        category = item
        pdfs = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
        if pdfs:
            print(f"📁 Folder: {category} ({len(pdfs)} PDF(s) found)")
            for f in pdfs:
                if upload_pdf(os.path.join(folder_path, f), category, existing_pdfs):
                    total_uploaded += 1
                else:
                    total_skipped += 1
            print()

print(f"\n✨ Done! Total PDFs added: {total_uploaded}, Skipped: {total_skipped}")
