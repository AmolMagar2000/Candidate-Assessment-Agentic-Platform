import os
from dotenv import load_dotenv
from chromadb import Client

# Load your .env file
load_dotenv("/home/ubuntu/ats-project/.env")
  # replace with your .env path

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TNS_NAME = os.getenv("DB_TNS_NAME")
WALLET_DIR = os.getenv("WALLET_DIR")

print("Loaded credentials for user:", DB_USER)

# Connect to ChromaDB if it's using these credentials
# (Assuming your ChromaDB client supports these env vars)
client = Client()

# List all collections
collections = client.list_collections()
print("Collections:", [col.name for col in collections])

# Loop through collections to show documents
for col in collections:
    collection = client.get_collection(col.name)
    documents = collection.get(include=["documents", "metadatas", "ids"])
    
    print(f"\n--- Collection: {col.name} ---")
    for doc, meta, doc_id in zip(documents['documents'], documents['metadatas'], documents['ids']):
        print(f"ID: {doc_id}")
        print(f"Document: {doc}")
        print(f"Metadata: {meta}")
        print("------")
