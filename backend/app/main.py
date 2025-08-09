import os
import string
import secrets
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, AnyHttpUrl
from pymongo import MongoClient
from pymongo.collection import Collection
from starlette.responses import RedirectResponse

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "urlshortener")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "urls")
SHORT_BASE_URL = os.getenv("SHORT_BASE_URL", "http://localhost:8000")
CODE_LENGTH = int(os.getenv("CODE_LENGTH", "7"))

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection: Collection = db[MONGO_COLLECTION]

app = FastAPI(title="URL Shortener API")

# CORS: allow localhost frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ShortenRequest(BaseModel):
    url: AnyHttpUrl


def generate_unique_code() -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(CODE_LENGTH))
        if not collection.find_one({"code": code}):
            return code


@app.on_event("startup")
def on_startup() -> None:
    # Ensure unique index on code
    collection.create_index("code", unique=True)
    collection.create_index("original_url")


@app.post("/api/shorten")
def create_short_url(payload: ShortenRequest):
    original_url = str(payload.url)

    # Optional: return existing mapping if URL already shortened
    existing = collection.find_one({"original_url": original_url})
    if existing:
        code = existing["code"]
        return {"code": code, "short_url": f"{SHORT_BASE_URL}/{code}"}

    code = generate_unique_code()
    doc = {"code": code, "original_url": original_url}
    collection.insert_one(doc)
    return {"code": code, "short_url": f"{SHORT_BASE_URL}/{code}"}


@app.get("/api/info/{code}")
def get_info(code: str):
    doc = collection.find_one({"code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Code not found")
    return {"code": doc["code"], "original_url": doc["original_url"], "short_url": f"{SHORT_BASE_URL}/{code}"}


@app.get("/{code}")
def redirect(code: str):
    doc = collection.find_one({"code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Code not found")
    return RedirectResponse(url=doc["original_url"], status_code=307)