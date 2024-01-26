from quart import Quart, render_template, websocket, send_from_directory

from hypercorn.asyncio import serve
from hypercorn.config import Config

import asyncio
import logging

app = Quart(__name__)

@app.route("/")
async def hello():
    return await render_template("index.html")

@app.route('/data/<path:path>')
async def serve_data_file(path):
    logging.info("Serving Data: %s/%s", app.outdir, path)
    return await send_from_directory(app.outdir, path)

@app.route('/<path:path>')
async def serve_frontend_file(path):
    return await send_from_directory('./frontend', path)

@app.websocket("/ws")
async def ws():
    while asyncio.current_task().cancelling():
        await websocket.send("hello")
        await websocket.send_json({"hello": "world"})

def create_task(args, hub):
    return asyncio.create_task(start(args, hub))

async def start(args, hub):
    app.outdir = args.outdir
    app.hub = hub
    config = Config()
    config.bind = ["localhost:5001"]
    config.certfile = 'cert.pem'
    config.keyfile = 'key.pem'
    return await serve(app, config)