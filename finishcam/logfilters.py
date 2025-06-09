import logging

class SuppressSSLErrorFilter(logging.Filter):
    """
    Filters out a specific and known-bogus SSL error that occurs when
    a client (e.g. browser) sends additional TLS data after cleanly 
    closing a connection.

    The error typically looks like:
        ssl.SSLError: [SSL: APPLICATION_DATA_AFTER_CLOSE_NOTIFY] ...
    
    It is harmless but shows up as a noisy traceback in asyncio logs,
    especially when using Hypercorn with HTTPS/HTTP2.
    """

    def filter(self, record):
        # Only filter if there's an exception attached to the log record
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info

            # Match exactly this known SSL error
            if (
                exc_type.__name__ == "SSLError"
                and "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in str(exc_value)
            ):
                return False  # suppress this log entry
        return True  # allow all other messages through


def apply_asyncio_ssl_filter():
    """
    Adds the SSL error suppression filter to the asyncio logger.
    This should be called very early in the application startup,
    before asyncio or Hypercorn emits any SSL-related logs.
    """
    logging.getLogger("asyncio").addFilter(SuppressSSLErrorFilter())
