# embedding/prompt_generator.py

import json
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict

# Load extracted functions
with open("function-map.json", "r") as f:
    all_functions = json.load(f)

# Load uncovered functions or fallback
if os.path.exists("uncovered-functions.json"):
    with open("uncovered-functions.json", "r") as f:
        uncovered_functions = json.load(f)
else:
    print("⚠️ No uncovered functions; falling back to all functions.")
    uncovered_functions = all_functions

# Initialize ChromaDB client (new syntax)
client = chromadb.PersistentClient(path="vectorstore")
collection = client.get_or_create_collection(name="functions")

# Embed and insert function chunks
for func in uncovered_functions:
    identifier = f"{func['filePath']}:{func['startLine']}-{func['endLine']}"
    metadata = {
        "filePath": func["filePath"],
        "name": func.get("name", "anonymous"),
        "startLine": func["startLine"],
        "endLine": func["endLine"],
        "type": func["type"],
        "class": func.get("class"),
    }
    collection.add(
        documents=[func["content"]],
        metadatas=[metadata],
        ids=[identifier]
    )

# For each uncovered function, find contextually related functions
prompt_batches = []
for func in uncovered_functions:
    identifier = f"{func['filePath']}:{func['startLine']}-{func['endLine']}"
    query = func["content"]
    results = collection.query(query_texts=[query], n_results=5)

    context_funcs = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        context_funcs.append({
            "name": meta["name"],
            "filePath": meta["filePath"],
            "startLine": meta["startLine"],
            "endLine": meta["endLine"],
            "content": doc
        })

    prompt_batches.append({
        "targetFunction": func,
        "relatedFunctions": context_funcs
    })

# Save prompt batch payloads
with open("generated-prompts.json", "w") as f:
    json.dump(prompt_batches, f, indent=2)

print(f"✅ Generated {len(prompt_batches)} LLM prompt batches.")
