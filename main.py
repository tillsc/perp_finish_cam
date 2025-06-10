import argparse
import asyncio
import logging
import sys
import time
import signal

import finishcam.grabber
import finishcam.webapp
import finishcam.preview
import finishcam.pubsub

from finishcam.logfilters import apply_shutdown_log_filter

# Suppress known noisy log entries (harmless shutdown-related warnings)
apply_shutdown_log_filter()

shutdown_event = asyncio.Event()
def setup_signal_handler(loop):
    """Registers SIGINT handler to gracefully cancel all running tasks."""
    def handle_shutdown():
        print("Shutdown requested via SIGINT")
        shutdown_event.set()
        for task in asyncio.all_tasks(loop):
            if not task.done():
                task.cancel()

    loop.add_signal_handler(signal.SIGINT, handle_shutdown)

async def start(args):
    # Setup logging level
    loglevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=loglevel)

    # Setup pub-sub hub and session name
    hub = finishcam.pubsub.Hub()
    session_name = time.strftime("%Y%m%d-%H%M%S")

    # Install SIGINT shutdown hook
    loop = asyncio.get_running_loop()
    setup_signal_handler(loop)

    # Prepare tasks
    tasks = []
    if not args.no_capture:
        tasks.append(finishcam.grabber.create_task(
            hub, session_name, args.outdir,
            args.time_span, args.fps, args.slot_width, args.left_to_right,
            shutdown_event,
            webp_quality=args.webp_quality, stamp_time=not args.no_stamp_time,
            test_mode=args.test_mode, stamp_fps=args.stamp_fps,
            video_capture_index=args.video_capture_index,
            resolution=args.resolution,
            debug=args.debug
        ))
        if args.preview:
            tasks.append(finishcam.preview.create_task(hub))
    if not args.no_webserver:
        tasks.append(finishcam.webapp.create_task(hub, session_name, args.outdir, shutdown_event))

    logging.info("Starting %i tasks", len(tasks))

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        logging.info("Shutdown signal received. Cancelling all tasks...")
        for task in tasks:
            task.cancel()
        done, pending = await asyncio.wait(tasks)

    # Handle any exceptions from completed tasks
    for task in done:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.exception("Task raised an exception: %s", e)

    # Cancel any remaining tasks
    for task in pending:
        task.cancel()


def main():
    parser = argparse.ArgumentParser(
        prog="perp_finish_cam", description="Takes slot cam based images and stores them"
    )
    parser.add_argument("outdir", default="data", nargs="?", help="Output directory (default: './data')")
    parser.add_argument("-p", "--preview", action="store_true", help="Show live preview windows")
    parser.add_argument("-l", "--left-to-right", action="store_true",
                        help="Race is coming from the left (default: from the right)")
    parser.add_argument("-t", "--time-span", type=int, default=10,
                        help="Time in seconds per destination image (default: 10)")
    parser.add_argument("-f", "--fps", type=int, default=30,
                        help="Frames per second to request from camera (default: 30)")
    parser.add_argument("-w", "--slot-width", type=int, default=2,
                        help="Default slot width when camera provides requested FPS (default: 2px)")
    parser.add_argument("-r", "--resolution",
                        choices=["qvga", "vga", "svga", "xga", "wxga", "hd", "sxga", "uxga", "fullhd", "4k"],
                        default="hd", help="Set resolution (default: hd = 1280x720)")
    parser.add_argument("-i", "--video-capture-index", type=int, default=0,
                        help="Index of the system camera to use (default: 0)")
    parser.add_argument("--no-stamp-time", action="store_true",
                        help="Do not print timestamp on each output image")
    parser.add_argument("--stamp-fps", action="store_true",
                        help="Print FPS on each output image")
    parser.add_argument("--test-mode", type=int,
                        help="Create the given amount of test images and exit")
    parser.add_argument("--webp-quality", type=int, default=90,
                        help="Quality for webp compression (default: 90)")
    parser.add_argument("--no-capture", action="store_true",
                        help="Disable capturing (webserver only)")
    parser.add_argument("--no-webserver", action="store_true",
                        help="Disable webserver (capturing only)")
    parser.add_argument("--debug", action="store_true", help="Start in debug mode (very noisy)")

    try:
        asyncio.run(start(parser.parse_args()))
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Exiting gracefully.")

if __name__ == "__main__":
    main()
