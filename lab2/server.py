#!/usr/bin/env python3
import socket
import os
import sys
import mimetypes
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote
from collections import deque
from typing import Dict, Deque, Tuple


class HTTPServerLab2:
    def __init__(
        self,
        directory: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        auto_port: bool = True,
        workers: int = 32,
        delay_sec: float = 1.0,
        counter_mode: str = "locked",
        rate_limit: int = 5,
        rate_window: float = 1.0,
    ):
        self.directory = os.path.abspath(directory)
        self.host = host
        self.port = port
        self.auto_port = auto_port
        self.socket: socket.socket | None = None

        # Concurrency & behavior settings
        self.workers = workers
        self.delay_sec = delay_sec
        self.counter_mode = counter_mode.lower()
        self.rate_limit = rate_limit
        self.rate_window = rate_window

        # Shared state
        self._counts: Dict[str, int] = {}
        self._counts_lock = threading.Lock()
        self._rate_map: Dict[str, Deque[float]] = {}
        self._rate_lock = threading.Lock()

        if not os.path.isdir(self.directory):
            raise ValueError(f"Directory '{directory}' does not exist")

    #  Port utils 
    def find_available_port(self, start_port, max_attempts=100):
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind((self.host, port))
                test_socket.close()
                return port
            except OSError:
                continue
        raise RuntimeError(
            f"Could not find available port in range {start_port}-{start_port + max_attempts}"
        )

    #  Rate limiting 
    def _allow_request(self, ip: str) -> bool:
        now = time.monotonic()
        with self._rate_lock:
            dq = self._rate_map.get(ip)
            if dq is None:
                dq = deque()
                self._rate_map[ip] = dq
            cutoff = now - self.rate_window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self.rate_limit:
                return False
            dq.append(now)
            return True

    #Counters 
    def _increment_count_locked(self, rel_path: str):
        with self._counts_lock:
            self._counts[rel_path] = self._counts.get(rel_path, 0) + 1

    def _increment_count_naive(self, rel_path: str):
        # Intentionally racy, with tiny sleep to increase interleaving
        if rel_path not in self._counts:
            self._counts[rel_path] = 0
            time.sleep(0.001)
        self._counts[rel_path] += 1

    def _increment_count(self, rel_path: str):
        if self.counter_mode == "naive":
            self._increment_count_naive(rel_path)
        else:
            self._increment_count_locked(rel_path)

    def _get_count(self, rel_path: str) -> int:
        with self._counts_lock:
            return self._counts.get(rel_path, 0)

    # -------------------- Server loop --------------------
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        original_port = self.port
        bind_successful = False

        try:
            self.socket.bind((self.host, self.port))
            bind_successful = True
        except OSError as e:
            if self.auto_port:
                print(f"Port {self.port} is already in use, searching for available port...")
                self.port = self.find_available_port(self.port + 1)
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind((self.host, self.port))
                bind_successful = True
                print(f"✓ Found available port: {self.port}")
            else:
                raise RuntimeError(
                    f"Port {self.port} is already in use. Use a different port or enable auto_port."
                ) from e

        if not bind_successful:
            raise RuntimeError(f"Failed to bind to port {self.port}")

        self.socket.listen(128)

        print(f"\n{'='*60}")
        print(f" Server started on http://{self.host}:{self.port}")
        print(f" Serving files from: {self.directory}")
        if self.port != original_port:
            print(f"  Note: Port {original_port} was in use, using {self.port} instead")
        print(f" Workers: {self.workers}, Delay: {self.delay_sec}s, Counter: {self.counter_mode}, Rate: {self.rate_limit}/s")
        print(f"{'='*60}")
        print("Press Ctrl+C to stop the server\n")

        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                while True:
                    client_socket, client_address = self.socket.accept()
                    # submit handling to pool
                    pool.submit(self._handle_client, client_socket, client_address)
        except KeyboardInterrupt:
            print("\n\n Shutting down server...")
        finally:
            if self.socket:
                self.socket.close()
            print("✓ Server stopped")

    #Request handling 
    def _handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        try:
            ip, _ = client_address
            if not self._allow_request(ip):
                self._send_response(client_socket, 429, "Too Many Requests", "text/plain", b"Rate limit exceeded\n")
                return

            # Artificial delay to simulate work (for concurrency measurement)
            if self.delay_sec > 0:
                time.sleep(self.delay_sec)

            request = client_socket.recv(4096).decode("utf-8", errors="ignore")
            if not request:
                return

            lines = request.split("\r\n")
            request_line = lines[0]
            print(f"Request: {request_line} from {client_address}")

            parts = request_line.split()
            if len(parts) < 2:
                self.send_response(client_socket, 400, "Bad Request", "text/html")
                return

            method = parts[0]
            path = unquote(parts[1])

            if method != "GET":
                self.send_response(client_socket, 405, "Method Not Allowed", "text/html")
                return

            if path.startswith("/"):
                path = path[1:]

            full_path = os.path.normpath(os.path.join(self.directory, path))
            if not full_path.startswith(self.directory):
                self.send_response(client_socket, 403, "Forbidden", "text/html")
                return

            if not path:
                full_path = self.directory

            if not os.path.exists(full_path):
                self.send_404(client_socket, path)
                return

            if os.path.isdir(full_path):
                # increment per-directory counter by relative path (count folder visits)
                rel = os.path.relpath(full_path, self.directory)
                if rel == '.':
                    rel = ''
                self._increment_count(rel)
                self.serve_directory(client_socket, full_path, path)
            else:
                # increment per-file counter by relative path
                rel = os.path.relpath(full_path, self.directory)
                self._increment_count(rel)
                self.serve_file(client_socket, full_path)

        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(client_socket, 500, "Internal Server Error", "text/html")
        finally:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            client_socket.close()

    # Response helpers 
    def serve_file(self, client_socket, file_path):
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

            header = self._build_headers(200, "OK", content_type, len(content))
            client_socket.sendall(header + content)
            print(f"✓ Served file: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"✗ Error serving file: {e}")
            self.send_response(client_socket, 500, "Internal Server Error", "text/html")

    def serve_directory(self, client_socket, dir_path, url_path):
        try:
            entries = os.listdir(dir_path)
            entries.sort()

            html = [
                "<!DOCTYPE html>",
                "<html>",
                "<head>",
                '<meta charset="utf-8">',
                f"<title>Directory listing for /{url_path}</title>",
                "<style>",
                "body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }",
                ".container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
                "h1 { color: #333; margin-top: 0; }",
                "ul { list-style: none; padding: 0; }",
                "li { padding: 12px; border-bottom: 1px solid #eee; transition: background 0.2s; }",
                "li:hover { background: #f9f9f9; }",
                "a { text-decoration: none; color: #0066cc; }",
                "a:hover { text-decoration: underline; }",
                ".dir { font-weight: bold; color: #d97706; }",
                '.dir:before { content: "📁 "; }',
                '.file:before { content: "📄 "; }',
                '.parent:before { content: "⬆️ "; }',
                "footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }",
                "</style>",
                "</head>",
                "<body>",
                '<div class="container">',
                f"<h1>📂 Directory listing for /{url_path}</h1>",
                "<ul>",
            ]

            if url_path:
                parent = "/".join(url_path.rstrip("/").split("/")[:-1])
                html.append(f'<li class="parent"><a href="/{parent}">Parent Directory</a></li>')

            for entry in entries:
                entry_path = os.path.join(dir_path, entry)
                url_entry = f"{url_path}/{entry}" if url_path else entry
                rel = os.path.relpath(entry_path, self.directory)
                if os.path.isdir(entry_path):
                    dcount = self._get_count(rel)
                    html.append(f'<li class="dir"><a href="/{url_entry}/">{entry}/</a> (requests: {dcount})</li>')
                else:
                    fcount = self._get_count(rel)
                    html.append(f'<li class="file"><a href="/{url_entry}">{entry}</a> (requests: {fcount})</li>')

            html.extend([
                "</ul>",
                "<footer>",
                f"<em>Python HTTP File Server - Port {self.port}</em>",
                "</footer>",
                "</div>",
                "</body>",
                "</html>",
            ])

            content = "\n".join(html).encode("utf-8")
            header = self._build_headers(200, "OK", "text/html; charset=utf-8", len(content))
            client_socket.sendall(header + content)
            print(f"✓ Served directory: {os.path.basename(dir_path) or 'root'}")
        except Exception as e:
            print(f"✗ Error serving directory: {e}")
            self.send_response(client_socket, 500, "Internal Server Error", "text/html")

    def send_404(self, client_socket, path):
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>404 Not Found</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }}
        h1 {{ color: #d9534f; font-size: 72px; margin: 0; }}
        h2 {{ color: #333; }}
        .path {{ background: #f8f8f8; padding: 10px; border-radius: 4px; font-family: monospace; word-break: break-all; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <h1>404</h1>
        <h2>Not Found</h2>
        <p>The requested file was not found on this server.</p>
        <p class=\"path\">/{path}</p>
        <hr>
        <p><em>Python HTTP File Server - Port {self.port}</em></p>
    </div>
</body>
</html>"""
        content_bytes = content.encode("utf-8")
        header = self._build_headers(404, "Not Found", "text/html; charset=utf-8", len(content_bytes))
        client_socket.sendall(header + content_bytes)
        print(f"✗ 404 Not Found: {path}")

    def send_response(self, client_socket, status_code, status_text, content_type):
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{status_code} {status_text}</title>
</head>
<body>
    <h1>{status_code} {status_text}</h1>
</body>
</html>"""
        content_bytes = content.encode("utf-8")
        header = self._build_headers(status_code, status_text, f"{content_type}; charset=utf-8", len(content_bytes))
        client_socket.sendall(header + content_bytes)

    def _send_response(self, client_socket, status_code, status_text, content_type, body_bytes):
        header = self._build_headers(status_code, status_text, content_type, len(body_bytes))
        client_socket.sendall(header + body_bytes)

    def _build_headers(self, code: int, text: str, content_type: str, content_length: int) -> bytes:
        response_headers = [
            f"HTTP/1.1 {code} {text}",
            f"Content-Type: {content_type}",
            f"Content-Length: {content_length}",
            "Connection: close",
            "",
            "",
        ]
        return "\r\n".join(response_headers).encode("utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python server_lab2.py <directory> [port]")
        print("Example: python server_lab2.py . 8080")
        sys.exit(1)

    directory = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    workers = int(os.environ.get("WORKERS", "32"))
    delay = float(os.environ.get("DELAY", "1.0"))
    counter_mode = os.environ.get("COUNTER_MODE", "locked")
    rate_limit = int(os.environ.get("RATE_LIMIT", "6"))
    rate_window = float(os.environ.get("RATE_WINDOW", "1.0"))

    try:
        server = HTTPServerLab2(
            directory,
            port=port,
            auto_port=True,
            workers=workers,
            delay_sec=delay,
            counter_mode=counter_mode,
            rate_limit=rate_limit,
            rate_window=rate_window,
        )
        server.start()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
