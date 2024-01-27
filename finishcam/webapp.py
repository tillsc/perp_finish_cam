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
app.config['TEMPLATES_AUTO_RELOAD'] = True

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
    with finishcam.pubsub.Subscription(app.hub) as queue:
        while not asyncio.current_task().done():
            (msg, data) = await queue.get()
            match msg:
                case 'live_image':
                    img_encode = cv.imencode('.webp', data, [cv.IMWRITE_WEBP_QUALITY, 30])[1] 
                    data_encode = np.array(img_encode) 
                    byte_encode = data_encode.tobytes() 

                    await websocket.send(byte_encode)

                    # Throw away everything happening since we started encoding and sending
                    while not queue.empty():
                        queue.get_nowait()

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