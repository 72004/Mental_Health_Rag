"""
Sukoon RAG: Gemini embeddings + Pinecone + Gemini generation
- Uses automatic embedding dimension detection.
- Deletes and recreates Pinecone index if dimension mismatch is found.
- Uses safe metadata (previews only) and stores full chunks locally.
"""

import os
import uuid
import time
import json
from google import genai
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# -----------------------
# CONFIG
# -----------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# ✅ default Pinecone environment (for free-tier AWS)
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD") or "aws"
PINECONE_REGION = os.getenv("PINECONE_REGION") or "us-east-1"

INDEX_NAME = "sukoon-rag-index"
N_BLOCKS_PER_CHUNK = 4
TOP_K = 5

# -----------------------
# INIT CLIENTS
# -----------------------
if not GEMINI_API_KEY:
    raise ValueError("Set GEMINI_API_KEY in your env or .env file.")
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
genai_client = genai.Client()

if not PINECONE_API_KEY:
    raise ValueError("Set PINECONE_API_KEY in your env or .env file.")
pc = Pinecone(api_key=PINECONE_API_KEY)

# -----------------------
# Load + chunk dataset
# -----------------------
def load_blocks_from_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    return blocks


def chunk_blocks(blocks: List[str], blocks_per_chunk: int) -> List[str]:
    return ["\n\n".join(blocks[i:i+blocks_per_chunk]) for i in range(0, len(blocks), blocks_per_chunk)]


dataset_path = "Data/Sukoon_AI_RAG_Dataset_v1.txt"
blocks = load_blocks_from_file(dataset_path)
chunks = chunk_blocks(blocks, N_BLOCKS_PER_CHUNK)
print(f"Loaded {len(blocks)} blocks -> {len(chunks)} chunks (approx)")

# -----------------------
# Embedding helper
# -----------------------
def embed_texts_with_gemini(texts: List[str], model="gemini-embedding-001") -> List[List[float]]:
    resp = genai_client.models.embed_content(model=model, contents=texts)
    raw_embs = resp.embeddings
    processed = []
    for item in raw_embs:
        if isinstance(item, (list, tuple)):
            vec = [float(x) for x in item]
        elif hasattr(item, "values"):
            vec = [float(x) for x in item.values]
        elif hasattr(item, "embedding"):
            vec = [float(x) for x in item.embedding]
        else:
            vec = [float(x) for x in list(item)]
        processed.append(vec)
    return processed

# -----------------------
# Auto-detect embedding dimension
# -----------------------
print("Detecting Gemini embedding dimension...")
sample_embs = embed_texts_with_gemini(chunks[:1])
EMBED_DIM = len(sample_embs[0])
print(f"Detected embedding dimension: {EMBED_DIM}")

# -----------------------
# Ensure Pinecone index dimension matches
# -----------------------
existing_indexes = {idx.name: idx for idx in pc.list_indexes()}

if INDEX_NAME in existing_indexes:
    info = pc.describe_index(INDEX_NAME)
    current_dim = info.dimension
    if current_dim != EMBED_DIM:
        print(f"Dimension mismatch (index={current_dim}, embedding={EMBED_DIM}). Recreating index...")
        pc.delete_index(INDEX_NAME)
        time.sleep(3)
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
        )
    else:
        print(f"Index '{INDEX_NAME}' exists with matching dimension ✅")
else:
    print(f"Creating Pinecone index '{INDEX_NAME}' with dim={EMBED_DIM}...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBED_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
    )

index = pc.Index(INDEX_NAME)
print("Connected to Pinecone index ✅")

# -----------------------
# Upsert embeddings (safe metadata + chunk_map)
# -----------------------
print("Embedding and preparing upsert with safe metadata...")

CHUNK_PREVIEW_LENGTH = 1000  # chars in metadata preview
chunk_map = {}

vectors_to_upsert = []
batch_size = 50
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    emb_result = embed_texts_with_gemini(batch)
    for j, emb in enumerate(emb_result):
        chunk_id = str(uuid.uuid4())
        full_text = batch[j]
        preview = full_text[:CHUNK_PREVIEW_LENGTH]
        meta = {"preview": preview, "source": "Sukoon_RAG"}
        vectors_to_upsert.append((chunk_id, [float(x) for x in emb], meta))
        chunk_map[chunk_id] = {"text": full_text}
    print(f"Embedded batch {i // batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")

# save chunk_map to disk
with open("chunk_map.json", "w", encoding="utf-8") as f:
    json.dump(chunk_map, f, ensure_ascii=False)

print(f"Prepared {len(vectors_to_upsert)} vectors; saved full chunks to chunk_map.json")

# Upsert in safe batches
UPsert_BATCH = 100
print("Upserting vectors to Pinecone (metadata previews only)...")
for i in range(0, len(vectors_to_upsert), UPsert_BATCH):
    batch = vectors_to_upsert[i:i+UPsert_BATCH]
    index.upsert(vectors=batch)
    print(f"Upserted batch {i // UPsert_BATCH + 1} / {(len(vectors_to_upsert)-1)//UPsert_BATCH + 1}")

print("Upsert complete ✅")

# -----------------------
# Crisis check
# -----------------------
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "i am going to die", "i want to die",
    "hurt myself", "self-harm", "want to end", "i can't go on"
]

def contains_crisis(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in CRISIS_KEYWORDS)

# -----------------------
# Retrieval + Generation
# -----------------------
# load chunk_map back into memory
if os.path.exists("chunk_map.json"):
    with open("chunk_map.json", "r", encoding="utf-8") as f:
        _CHUNK_MAP = json.load(f)
else:
    _CHUNK_MAP = {}

# Helper: normalize embedding objects -> list[float]
# -----------------------
def normalize_embedding(emb_obj) -> List[float]:
    """
    Convert various embedding shapes returned by Gemini SDK into a plain Python list of floats.
    Handles: list/tuple, objects with .values, objects with .embedding, or other iterable wrappers.
    """
    # plain list or tuple
    if isinstance(emb_obj, (list, tuple)):
        return [float(x) for x in emb_obj]

    # object with .values attribute (dict-like)
    if hasattr(emb_obj, "values"):
        try:
            return [float(x) for x in emb_obj.values]
        except Exception:
            pass

    # object with .embedding attribute
    if hasattr(emb_obj, "embedding"):
        try:
            return [float(x) for x in emb_obj.embedding]
        except Exception:
            pass

    # try to coerce to list (final fallback)
    try:
        return [float(x) for x in list(emb_obj)]
    except Exception as e:
        raise ValueError(f"Cannot normalize embedding object to list[float]: {e}")

# -----------------------
# Replacement: Retrieval function (query -> top-k chunks)
# -----------------------
def retrieve_top_k(query: str, top_k: int = TOP_K):
    # 1) get raw embedding from Gemini
    raw = genai_client.models.embed_content(model="gemini-embedding-001", contents=[query])
    # raw.embeddings may be a list-like; grab first item
    raw_emb_item = None
    try:
        raw_emb_item = raw.embeddings[0]
    except Exception:
        # defensive: if SDK shape differs, try alternative attributes
        if hasattr(raw, "embeddings"):
            raw_emb_item = raw.embeddings
        elif hasattr(raw, "data"):
            # sometimes responses nest under .data
            raw_emb_item = raw.data[0].embedding if raw.data and hasattr(raw.data[0], "embedding") else raw
        else:
            raw_emb_item = raw

    # 2) normalize to plain list[float]
    q_emb = normalize_embedding(raw_emb_item)

    # 3) use Pinecone query (vector must be list[float])
    resp = index.query(vector=q_emb, top_k=top_k, include_metadata=True)

    # 4) map matches to full text using local chunk_map if available
    hits = []
    for m in resp.matches:
        chunk_id = m.id
        full_text = _CHUNK_MAP.get(chunk_id, {}).get("text") if "_CHUNK_MAP" in globals() else None
        if not full_text:
            full_text = (m.metadata.get("preview") if m.metadata else "") or ""
        hits.append({"id": chunk_id, "score": m.score, "text": full_text})
    return hits


def compose_prompt(user_text: str, retrieved_chunks: List[Dict]) -> str:
    context = "\n\n".join([f"- {c['text']}" for c in retrieved_chunks if c['text']])
    return f"""
You are Sukoon AI — a calm, kind, big-brother style mental health companion. 
Use the context below (do not invent facts). Respond empathetically, in short paragraphs (3–5), practical, and supportive and also suggest some exercises or activities that the user can do to improve their mental health.
If the user shows crisis signs, respond with empathy and encourage immediate help.

Context:
{context}

User: {user_text}

Sukoon AI:
"""


def generate_reply_with_gemini(prompt: str, model="gemini-2.5-flash", max_output_tokens=300):
    response = genai_client.models.generate_content(model=model, contents=prompt)
    if hasattr(response, "text"):
        return response.text
    try:
        return "".join([c.get("text", "") for c in response.output])
    except Exception:
        return str(response)


def handle_user_input(user_input: str):
    if contains_crisis(user_input):
        return ("I’m really sorry you’re feeling so overwhelmed. I’m not equipped to provide emergency help. "
                "If you are in immediate danger or think you might harm yourself, please contact your local emergency services "
                "or a suicide prevention hotline. Would you like help finding local resources?")
    hits = retrieve_top_k(user_input, TOP_K)
    prompt = compose_prompt(user_input, hits)
    return generate_reply_with_gemini(prompt)

# -----------------------
# Quick test
# -----------------------
if __name__ == "__main__":
    test_query = "I feeling sad and i want to die"
    print("User query:", test_query)
    print("---")
    print(handle_user_input(test_query))
