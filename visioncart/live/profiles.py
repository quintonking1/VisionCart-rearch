"""Live demo profiles: a real Pinterest board for style memory, the open web for products."""
from __future__ import annotations

from visioncart import config
from visioncart.agents.types import Deps
from visioncart.graph import load_blend, load_threshold
from visioncart.live.web_catalog import LiveCatalog
from visioncart.live.worker import run_live_worker
from visioncart.llm import LLMClient
from visioncart.memory.store import MemoryStore

LIVE_USERS = {
    "quinn": {"name": "Quinn King", "about": "Pinterest · mens-outfits",
              "board_url": "https://www.pinterest.com/quinnkingqk/mens-outfits/"},
}


def make_live_deps(llm: LLMClient, store: MemoryStore, user_id: str, catalog: LiveCatalog,
                   progress=None) -> Deps:
    return Deps(llm=llm, catalog=catalog, search=None, memory=store.load(user_id),
                threshold=load_threshold(), blend=load_blend(), worker=run_live_worker,
                max_retries=config.LIVE_MAX_RETRIES, progress=progress)
