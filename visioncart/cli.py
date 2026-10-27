"""Demo CLI.

    python -m visioncart.cli users
    python -m visioncart.cli sync jordan
    python -m visioncart.cli ask jordan "a vase and a pendant light for my living room, under $300 total"
    python -m visioncart.cli feedback jordan <product_id> like --cluster 0
"""
from __future__ import annotations

import argparse
import asyncio

from visioncart.catalog.store import Catalog
from visioncart.graph import make_deps, run
from visioncart.memory import feedback
from visioncart.memory.store import MemoryStore
from visioncart.memory.sync import sync_user
from visioncart.memory.users import DEMO_USERS, user_pins


async def _sync(llm, store, user_id: str, force: bool = False):
    mem = await sync_user(llm, store, user_id, user_pins(user_id), force=force)
    print(f"{user_id}: {len(mem.clusters)} style cluster(s)")
    for c in mem.clusters:
        print(f"  [{c.id}] {c.name} (weight {c.weight:.2f}, {len(c.pins)} pins)\n      {c.persona}")
    return mem


async def main() -> None:
    ap = argparse.ArgumentParser(prog="visioncart")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("users")
    s = sub.add_parser("sync")
    s.add_argument("user")
    s.add_argument("--force", action="store_true")
    a = sub.add_parser("ask")
    a.add_argument("user")
    a.add_argument("request")
    f = sub.add_parser("feedback")
    f.add_argument("user")
    f.add_argument("product_id")
    f.add_argument("action", choices=sorted(feedback.TERM_STEP))
    f.add_argument("--cluster", type=int, required=True)
    args = ap.parse_args()

    if args.cmd == "users":
        for uid, u in DEMO_USERS.items():
            print(f"{uid:8} {u['about']:24} boards: {', '.join(u['boards'])}")
        return

    store = MemoryStore()
    if args.cmd == "feedback":
        c = feedback.record(store, args.user, args.cluster, Catalog.load().get(args.product_id), args.action)
        liked, disliked = c.learned_terms()
        print(f"cluster {c.id} weight {c.weight:.2f} | more: {', '.join(liked)} | less: {', '.join(disliked)}")
        return

    from visioncart.llm import OpenAILLM
    llm = OpenAILLM()
    if args.cmd == "sync":
        await _sync(llm, store, args.user, args.force)
    elif args.cmd == "ask":
        await _sync(llm, store, args.user)  # no-op unless the board changed
        from visioncart.agents.presenter import render_text
        out = await run(args.request, make_deps(llm, store, args.user))
        print(render_text(out["sections"]))


if __name__ == "__main__":
    asyncio.run(main())
