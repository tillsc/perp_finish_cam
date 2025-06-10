from quart import Quart, render_template, websocket, send_from_directory

from hypercorn.asyncio import serve
from hypercorn.config import Config

import numpy as np
import cv2 as cv
import json
import asyncio
import logging
from datetime import datetime

import finishcam.pubsub

app = Quart(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.active_ws_tasks = set()  # Track live WebSocket tasks for cancellation


@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Pragma"] = "no-cache"
    return r


@app.route("/")
async def home():
    last_image_url = "/data/%s/img%s.webp" % (app.session_name, "0")  # TODO
    return await render_template(
        "index.html.jinja",
        session_name=app.session_name, last_image_url=last_image_url,
        start_time=app.virtual_start_time,
        demo_time=datetime.now().strftime("%H:%M:%S.123"),
    )


@app.route("/data/<path:path>")
async def serve_data_file(path):
    logging.info("Serving data: %s/%s", app.outdir, path)
    return await send_from_directory(app.outdir, path)


@app.route("/js/<path:path>")
async def serve_js_file(path):
    logging.info("Serving js file: %s/%s", "./js", path)
    return await send_from_directory("./js", path)


@app.websocket("/ws/live")
async def ws_live():
    task = asyncio.current_task()
    app.active_ws_tasks.add(task)
    try:
        last_index = None
        with finishcam.pubsub.Subscription(app.hub) as event:
            while True:
                await event.wait()
                if "live_image" in app.hub.data:
                    fut = None
                    metadata = app.hub.data["live_metadata"]
                    if last_index != metadata['index']:
                        json_bytes = bytearray(json.dumps(metadata), 'utf-8')
                        try:
                            fut = websocket.send(np.insert(json_bytes, 0, 1))
                        except Exception as e:
                            logging.debug("Metadata send failed: %s", e)
                        last_index = metadata['index']

                    retval, buf = await asyncio.to_thread(cv.imencode,
                        ".webp", app.hub.data["live_image"], [cv.IMWRITE_WEBP_QUALITY, 30]
                    )

                    try:
                        if fut is not None:
                            await fut
                        await websocket.send(np.insert(buf, 0, 0))
                    except Exception as e:
                        logging.debug("Image send failed: %s", e)

                await asyncio.sleep(.3)
                event.clear()
    except asyncio.CancelledError:
        logging.info("WebSocket task was cancelled")
    finally:
        app.active_ws_tasks.discard(task)
        try:
            await websocket.close()
        except Exception as e:
            logging.debug("WebSocket close failed: %s", e)


def create_task(hub, session_name, outdir, shutdown_event):
    return asyncio.create_task(start(hub, session_name, outdir, shutdown_event))


async def start(hub, session_name, outdir, shutdown_event: asyncio.Event):
    app.hub = hub
    app.session_name = session_name
    app.outdir = outdir
    app.virtual_start_time = datetime.now()
    app.active_ws_tasks = set()  # Ensure fresh tracking on each run

    config = Config()
    config.bind = ["0.0.0.0:5001"]
    config.certfile = "cert.pem"
    config.keyfile = "key.pem"

    try:
        await serve(app, config, shutdown_trigger=shutdown_event.wait)
    finally:
        # Clean shutdown: cancel all WebSocket tasks
        for task in list(app.active_ws_tasks):
            task.cancel()
        await asyncio.gather(*app.active_ws_tasks, return_exceptions=True)
