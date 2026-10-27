import argparse

import uvicorn

ap = argparse.ArgumentParser(prog="python -m visioncart.web")
ap.add_argument("--host", default="127.0.0.1")
ap.add_argument("--port", type=int, default=8000)
args = ap.parse_args()
uvicorn.run("visioncart.web.app:app", host=args.host, port=args.port)
