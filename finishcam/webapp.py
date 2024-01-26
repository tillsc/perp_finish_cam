from quart import Quart, render_template, websocket, send_from_directory

from hypercorn.asyncio import serve
from hypercorn.config import Config

import json
import asyncio
import logging

app = Quart(__name__)

@app.route("/")
async def home():
    with open('%s/index.json' % app.outdir) as f:
        data = json.load(f)
        session = list(data)[-1]
        last_image_url = "/data/%s/img%s.webp" % (session, data[session]['last_index'])
        return await render_template("index.html.jinja", last_image_url=last_image_url)

@app.route('/data/<path:path>')
async def serve_data_file(path):
    logging.info("Serving data: %s/%s", app.outdir, path)
    return await send_from_directory(app.outdir, path)

@app.route('/<path:path>')
async def serve_frontend_file(path):
    logging.info("Serving static file: %s/%s", './static', path)
    return await send_from_directory('./static', path)

@app.websocket("/ws")
async def ws():
    while asyncio.current_task().done():
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