def send_response(self, client_socket, status_code, status_text, content_type):
    """Send a simple HTTP response"""
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
    response_headers = [
        f"HTTP/1.1 {status_code} {status_text}",
        f"Content-Type: {content_type}; charset=utf-8",
        f"Content-Length: {len(content_bytes)}",
        "Connection: close",
        "",
        "",
    ]

    header = "\r\n".join(response_headers).encode("utf-8")
    client_socket.sendall(header + content_bytes)
