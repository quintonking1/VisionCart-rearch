"""Thin async OpenAI wrapper: structured outputs, embeddings, and a disk cache.

The cache keeps eval runs reproducible and avoids paying twice for the same call.
`openai` is imported lazily so code-only tests run without it installed.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Protocol, Sequence, TypeVar

import numpy as np
from pydantic import BaseModel

from visioncart import config

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    async def parse(self, schema: type[T], system: str, user: str,
                    images: Sequence[str | Path] = (), model: str | None = None) -> T: ...

    async def embed(self, texts: Sequence[str]) -> np.ndarray: ...


def _sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode())
        h.update(b"\x00")
    return h.hexdigest()


def file_sha(path: str | Path) -> str:
    return hashlib.sha256(config.resolve(path).read_bytes()).hexdigest()


def _data_url(path: str | Path) -> str:
    p = config.resolve(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def normalize(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    return m / np.clip(norms, 1e-8, None)


class OpenAILLM:
    def __init__(self, cache_dir: Path = config.CACHE_DIR):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(max_retries=4)
        self.sem = asyncio.Semaphore(config.MAX_CONCURRENCY)
        self.parse_cache = cache_dir / "parse"
        self.embed_cache = cache_dir / "embed"
        self.parse_cache.mkdir(parents=True, exist_ok=True)
        self.embed_cache.mkdir(parents=True, exist_ok=True)

    async def parse(self, schema, system, user, images=(), model=None):
        model = model or (config.VISION_MODEL if images else config.CHAT_MODEL)
        key = _sha(model, system, user, json.dumps(schema.model_json_schema(), sort_keys=True),
                   *[file_sha(i) for i in images])
        path = self.parse_cache / f"{key}.json"
        if path.exists():
            return schema.model_validate_json(path.read_text())

        content = [{"type": "input_text", "text": user}]
        content += [{"type": "input_image", "image_url": _data_url(i)} for i in images]
        async with self.sem:
            resp = await self.client.responses.parse(
                model=model,
                instructions=system,
                input=[{"role": "user", "content": content}],
                text_format=schema,
            )
        out = resp.output_parsed
        if out is None:
            raise RuntimeError(f"{schema.__name__}: model returned no parsed output")
        path.write_text(out.model_dump_json())
        return out

    async def embed(self, texts):
        texts = list(texts)
        keys = [_sha(config.EMBED_MODEL, t) for t in texts]
        vecs: dict[int, list[float]] = {}
        missing = []
        for i, k in enumerate(keys):
            p = self.embed_cache / f"{k}.json"
            if p.exists():
                vecs[i] = json.loads(p.read_text())
            else:
                missing.append(i)
        for start in range(0, len(missing), 256):
            batch = missing[start:start + 256]
            async with self.sem:
                resp = await self.client.embeddings.create(
                    model=config.EMBED_MODEL, input=[texts[i] for i in batch])
            for i, d in zip(batch, resp.data):
                vecs[i] = d.embedding
                (self.embed_cache / f"{keys[i]}.json").write_text(json.dumps(d.embedding))
        return normalize(np.array([vecs[i] for i in range(len(texts))]))
