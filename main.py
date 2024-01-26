import argparse
import asyncio
import logging
import sys

import finishcam.grabber
import finishcam.webapp
import finishcam.preview

async def start(args):
    loglevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=loglevel)

    grabber = finishcam.grabber.Grabber(
        args.outdir,
        args.time_span,
        args.px_per_second,
        args.preview,
        args.left_to_right,
        webp_quality=args.webp_quality,
        stamp_time=not args.no_stamp_time,
        test_mode=args.test_mode,
        stamp_fps=args.stamp_fps,
        debug=args.debug
    )

    tasks = [
        grabber.create_task(),
        finishcam.webapp.create_task(args, grabber.hub)
        ]
    if args.preview:
        tasks.append(finishcam.preview.create_task(args, grabber.hub))
    
    logging.debug('Starting tasks')
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in done:
        task.result() # Raise exceptions if there are any
    for task in pending:
        task.cancel()


parser = argparse.ArgumentParser(
    prog="perp_finish_cam", description="Takes slot cam based images and stores them"
)

parser.add_argument(
    "outdir", default="data", nargs="?", help="Output directory (default: './data')"
)

parser.add_argument(
    "-p", "--preview", action="store_true", help="Show live preview windows"
)
parser.add_argument(
    "-l",
    "--left-to-right",
    action="store_true",
    help="Race is comming from the left (default: race is coming from the right)",
)

parser.add_argument(
    "-t",
    "--time-span",
    type=int,
    default=10,
    help="Time in seconds per destination image (default: 10 seconds)",
)
parser.add_argument(
    "-x",
    "--px-per-second",
    type=int,
    default=2 * 29,
    help="Width on one second in destination image (default: 2px * 29frames/seconds = 58px/second)",
)

parser.add_argument(
    "--no-stamp-time",
    action="store_true",
    help="Do not print timestamp on each output image",
)
parser.add_argument(
    "--stamp-fps", action="store_true", help="Print FPS on each output image"
)

parser.add_argument(
    "--test-mode", type=int, help="Create the given amount of test images and exit"
)
parser.add_argument(
    "--webp-quality",
    type=int,
    default=90,
    help="Quality for webp compression (default: 90)",
)
parser.add_argument(
    "--debug", action="store_true", help="Debug Mode"
)

asyncio.run(start(parser.parse_args()))
