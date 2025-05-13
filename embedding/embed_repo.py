# File: embedding/embed_repo.py
import json
import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
import requests

# Load Azure credentials from .env
load_dotenv()
AZURE_INSTANCE = os.getenv("AZURE_OPENAI_INSTANCE_NAME")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_API_EMBEDDING_DEPLOYMENT_NAME")
AZURE_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")

assert AZURE_INSTANCE and AZURE_DEPLOYMENT and AZURE_KEY, "Azure credentials missing"

# Azure OpenAI endpoint for embedding
EMBED_URL = f"https://{AZURE_INSTANCE}.openai.azure.com/openai/deployments/{AZURE_DEPLOYMENT}/embeddings?api-version=2023-05-15"

HEADERS = {
    "Content-Type": "application/json",
    "api-key": AZURE_KEY,
}

# Load function map
with open("function-map.json", "r") as f:
    functions = json.load(f)

# Initialize ChromaDB with DuckDB+Parquet backend
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="vectorstore",
    anonymized_telemetry=False
))

# Create or get collection
try:
    collection = client.get_or_create_collection("function_chunks")
except Exception:
    collection = client.create_collection("function_chunks")

# Embed and store
for i, fn in enumerate(functions):
    chunk_id = f"fn_{i}_{fn.get('name')}"
    content = fn.get('content')

    try:
        response = requests.post(
            EMBED_URL, headers=HEADERS, json={"input": content}
        )
        response.raise_for_status()
        embedding = response.json()["data"][0]["embedding"]

        collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[{
                "file": fn.get("filePath"),
                "name": fn.get("name"),
                "class": fn.get("class"),
                "type": fn.get("type"),
            }],
            ids=[chunk_id]
        )
        print(f"✅ Embedded {fn.get('name')} ({fn.get('filePath')})")

    except Exception as e:
        print(f"❌ Failed to embed {fn.get('name')}: {e}")

# Persist to disk (if supported)
try:
    client.persist()
    print("✅ All functions embedded and persisted in ChromaDB.")
except Exception:
    print("⚠️ ChromaDB client does not support explicit persist; data saved automatically.")
