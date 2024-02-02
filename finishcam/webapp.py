from quart import Quart, render_template, websocket, send_from_directory

from hypercorn.asyncio import serve
from hypercorn.config import Config

import numpy as np
import cv2 as cv
import json
import asyncio
import logging

import finishcam.pubsub

app = Quart(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    return r


@app.route("/")
async def home():
    last_image_url = "/data/%s/img%s.webp" % (app.session_name, "0") # TODO
    return await render_template(
        "index.html.jinja", 
        session_name=app.session_name, last_image_url=last_image_url
    )

@app.route("/sessions/<string:session_name>")
async def session(session_name):
    return await render_template(
        "session.html.jinja", 
        session_name=session_name
    )

@app.route("/data/<path:path>")
async def serve_data_file(path):
    logging.info("Serving data: %s/%s", app.outdir, path)
    return await send_from_directory(app.outdir, path)


@app.route("/<path:path>")
async def serve_frontend_file(path):
    logging.info("Serving static file: %s/%s", "./static", path)
    return await send_from_directory("./static", path)


@app.websocket("/ws/live")
async def ws_live():
    last_index = None
    with finishcam.pubsub.Subscription(app.hub) as queue:
        while not asyncio.current_task().done():
            (msg, metadata, data) = await queue.get()
            match msg:
                case "live_image":
                    fut = None
                    if last_index != metadata['index']:
                        json_bytes = bytearray(json.dumps(metadata), 'utf-8')
                        fut = websocket.send(np.insert(json_bytes, 0, 1))
                        last_index = metadata['index']
                    
                    retval, buf	= cv.imencode(
                        ".webp", data, [cv.IMWRITE_WEBP_QUALITY, 30]
                    )

                    if fut != None:
                        await fut
                
                    await websocket.send(np.insert(buf, 0, 0))

                    await asyncio.sleep(.1)
                    # Throw away everything happening since we started encoding and sending
                    while not queue.empty():
                        queue.get_nowait()


def create_task(hub, session_name, outdir):
    return asyncio.create_task(start(hub, session_name, outdir))


async def start(hub, session_name, outdir):
    app.hub = hub
    app.session_name = session_name
    app.outdir = outdir

    config = Config()
    config.bind = ["localhost:5001"]
    config.certfile = "cert.pem"
    config.keyfile = "key.pem"
    return await serve(app, config)
