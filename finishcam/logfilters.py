import logging


class SuppressBenignShutdownErrors(logging.Filter):
    """
    Filters out harmless but noisy exceptions that occur during application shutdown.

    This includes:
    - ssl.SSLError: [SSL: APPLICATION_DATA_AFTER_CLOSE_NOTIFY] ...
      Happens when a client sends extra TLS data after closing the connection.
    
    - RuntimeError: TaskGroup ... is shutting down
      Happens when Hypercorn is shutting down and still cleaning up async tasks.

    These exceptions are expected during shutdown and do not indicate real problems.
    """

    def filter(self, record):
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info

            # SSL noise on client disconnect
            if (
                exc_type.__name__ == "SSLError"
                and "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in str(exc_value)
            ):
                return False  # suppress this log entry

            # Hypercorn's TaskGroup shutdown noise
            if (
                exc_type.__name__ == "RuntimeError"
                and "TaskGroup" in str(exc_value)
                and "is shutting down" in str(exc_value)
            ):
                return False  # suppress this log entry

        return True  # allow all other messages


def apply_shutdown_log_filter():
    """
    Attaches the shutdown noise filter to the asyncio logger.
    Call this once early in your application (e.g., in main.py).
    """
    logging.getLogger("asyncio").addFilter(SuppressBenignShutdownErrors())
