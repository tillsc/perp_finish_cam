import time
import argparse
import threading
import asyncio

from quart import Quart, send_from_directory
from hypercorn.asyncio import serve
from hypercorn.config import Config

import grabber

async def start(args):
    tasks = [create_task(startStaticWebserver(args)),
            create_task(startGrabber(args))]
    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in tasks:
        task.cancel()

def create_task(awaitable):
    return asyncio.get_running_loop().create_task(awaitable)

async def startStaticWebserver(args):
    app = Quart(__name__)

    @app.route('/data/<path:path>')
    async def serve_data_file(path):
        return await send_from_directory(args.outdir, path)

    @app.route('/<path:path>')
    async def serve_frontend_file(path):
        return await send_from_directory('./frontend', path)

    config = Config()
    config.bind = ["localhost:5001"]
    config.certfile = 'cert.pem'
    config.keyfile = 'key.pem'
    return await serve(app, config)

async def startGrabber(args):
    session_name = time.strftime("%Y%m%d-%H%M%S")

    gr = grabber.Grabber(args.outdir, 
        args.time_span, args.px_per_second, 
        args.preview, args.left_to_right,
        webp_quality = args.webp_quality,
        stamp_time = not args.no_stamp_time,
        test_mode = args.test_mode,
        stamp_fps = args.stamp_fps)
    return await gr.start(session_name)

parser = argparse.ArgumentParser(
                    prog='perp_finish_cam',
                    description='Takes slot cam based images and stores them')

parser.add_argument('outdir', default = 'data', nargs = '?', help = "Output directory (default: './data')") 

parser.add_argument('-p', '--preview', action='store_true', help = 'Show live preview windows') 
parser.add_argument('-l', '--left-to-right', action='store_true', help = 'Race is comming from the left (default: race is coming from the right)') 

parser.add_argument('-t', '--time-span', type = int, default = 10, help = 'Time in seconds per destination image (default: 10 seconds)')
parser.add_argument('-x', '--px-per-second', type = int, default = 2*29, help = 'Width on one second in destination image (default: 2px * 29frames/seconds = 58px/second)')

parser.add_argument('--no-stamp-time', action='store_true', help = 'Do not print timestamp on each output image') 
parser.add_argument('--stamp-fps', action='store_true', help = 'Print FPS on each output image') 

parser.add_argument('--test-mode', type = int, help = 'Create the given amount of test images and exit') 
parser.add_argument('--webp-quality', type = int, default = 90, help = 'Quality for webp compression (default: 90)') 

args = parser.parse_args()

asyncio.run(start(args))