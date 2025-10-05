def send_404(self, client_socket, path):
    """Send 404 Not Found response"""
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
    <div class="container">
        <h1>404</h1>
        <h2>Not Found</h2>
        <p>The requested file was not found on this server.</p>
        <p class="path">/{path}</p>
        <hr>
        <p><em>Python HTTP File Server - Port {self.port}</em></p>
    </div>
</body>
</html>"""

    content_bytes = content.encode("utf-8")
    response_headers = [
        "HTTP/1.1 404 Not Found",
        "Content-Type: text/html; charset=utf-8",
        f"Content-Length: {len(content_bytes)}",
        "Connection: close",
        "",
        "",
    ]

    header = "\r\n".join(response_headers).encode("utf-8")
    client_socket.sendall(header + content_bytes)
    print(f"✗ 404 Not Found: {path}")
