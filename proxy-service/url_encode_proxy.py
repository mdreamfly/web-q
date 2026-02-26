"""
Lightweight TCP proxy that URL-encodes non-ASCII bytes in HTTP request lines
before forwarding to uvicorn. This enables direct use of Chinese (and other
non-ASCII) characters in URLs without requiring client-side encoding.

Handles encoding detection: if the client sends non-UTF-8 bytes (e.g. GBK from
Windows terminals), the proxy will transcode to UTF-8 before percent-encoding.
"""

import asyncio
import logging
import re
import sys
import subprocess
import signal
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("url_encode_proxy")

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8001
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8002

# Match bytes that are NOT valid unencoded URI characters
# Valid: unreserved + reserved per RFC 3986
# unreserved = A-Z a-z 0-9 - . _ ~
# reserved   = : / ? # [ ] @ ! $ & ' ( ) * + , ; =
# percent    = %
NON_ASCII_RE = re.compile(rb'[\x80-\xff]+')

# Encodings to try when the bytes are not valid UTF-8.
# Order matters: most common Windows CJK encodings first.
FALLBACK_ENCODINGS = ['gbk', 'gb2312', 'gb18030', 'big5', 'euc-kr', 'shift_jis', 'euc-jp']


def _transcode_to_utf8(raw: bytes) -> bytes:
    """
    Attempt to interpret raw bytes as UTF-8. If that fails, try common CJK
    encodings and return the UTF-8 equivalent. Falls back to the original
    bytes if nothing works.
    """
    # Already valid UTF-8?
    try:
        raw.decode('utf-8')
        return raw
    except UnicodeDecodeError:
        pass

    # Try fallback encodings
    for enc in FALLBACK_ENCODINGS:
        try:
            decoded = raw.decode(enc)
            utf8_bytes = decoded.encode('utf-8')
            logger.info(f"Transcoded non-ASCII bytes from {enc} to UTF-8: {decoded}")
            return utf8_bytes
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue

    # Give up — return original bytes
    logger.warning(f"Could not detect encoding for bytes: {raw!r}")
    return raw


def encode_non_ascii_in_request_line(request_line: bytes) -> bytes:
    """
    URL-encode any non-ASCII bytes found in the HTTP request line.
    If the bytes are not valid UTF-8 (e.g. GBK from Windows), they are first
    transcoded to UTF-8 before percent-encoding.

    Example (UTF-8 input):
        b'GET /search?q=\\xe4\\xbb\\x8a\\xe5\\xa4\\xa9 HTTP/1.1\\r\\n'
        -> b'GET /search?q=%E4%BB%8A%E5%A4%A9 HTTP/1.1\\r\\n'

    Example (GBK input, 今天):
        b'GET /search?q=\\xbd\\xf1\\xcc\\xec HTTP/1.1\\r\\n'
        -> b'GET /search?q=%E4%BB%8A%E5%A4%A9 HTTP/1.1\\r\\n'
    """
    # Split into parts: METHOD TARGET HTTP/x.x
    parts = request_line.split(b' ', 2)
    if len(parts) != 3:
        return request_line

    method, target, version = parts

    # First, transcode non-ASCII segments to UTF-8 if needed
    def transcode_match(m):
        return _transcode_to_utf8(m.group(0))

    utf8_target = NON_ASCII_RE.sub(transcode_match, target)

    # Now percent-encode any non-ASCII bytes (which are now guaranteed UTF-8)
    def encode_match(m):
        return quote(m.group(0), safe='').encode('ascii')

    encoded_target = NON_ASCII_RE.sub(encode_match, utf8_target)

    logger.debug(f"Request line: {method} {encoded_target} (original target: {target!r})")
    return method + b' ' + encoded_target + b' ' + version


async def pipe(reader, writer):
    """Pipe data from reader to writer."""
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(client_reader, client_writer):
    """Handle an incoming client connection."""
    upstream_reader = None
    upstream_writer = None
    try:
        # Connect to upstream uvicorn
        upstream_reader, upstream_writer = await asyncio.open_connection(
            UPSTREAM_HOST, UPSTREAM_PORT
        )

        # Read the first line (HTTP request line)
        request_line = await asyncio.wait_for(
            client_reader.readline(), timeout=10.0
        )
        if not request_line:
            return

        # Encode non-ASCII characters in the request line
        encoded_line = encode_non_ascii_in_request_line(request_line)
        upstream_writer.write(encoded_line)
        await upstream_writer.drain()

        # Pipe the rest bidirectionally
        await asyncio.gather(
            pipe(client_reader, upstream_writer),
            pipe(upstream_reader, client_writer),
        )
    except (ConnectionRefusedError, asyncio.TimeoutError) as e:
        error_response = (
            b"HTTP/1.1 502 Bad Gateway\r\n"
            b"Content-Type: text/plain\r\n"
            b"Connection: close\r\n\r\n"
            b"Upstream service unavailable\r\n"
        )
        try:
            client_writer.write(error_response)
            await client_writer.drain()
        except Exception:
            pass
    except Exception:
        pass
    finally:
        for w in (client_writer, upstream_writer):
            if w:
                try:
                    w.close()
                    await w.wait_closed()
                except Exception:
                    pass


async def main():
    # Start uvicorn as a subprocess on the internal port
    uvicorn_proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", UPSTREAM_HOST,
        "--port", str(UPSTREAM_PORT),
        "--http", "h11",
        "--log-level", "info",
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # Wait a moment for uvicorn to start
    await asyncio.sleep(2)

    # Start the TCP proxy server
    server = await asyncio.start_server(
        handle_client, LISTEN_HOST, LISTEN_PORT
    )
    print(f"URL-encoding proxy listening on {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"Forwarding to uvicorn on {UPSTREAM_HOST}:{UPSTREAM_PORT}")

    # Handle shutdown gracefully
    loop = asyncio.get_event_loop()

    def shutdown():
        uvicorn_proc.terminate()
        server.close()

    try:
        # On Unix, register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, shutdown)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        pass
    finally:
        uvicorn_proc.terminate()
        await uvicorn_proc.wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
