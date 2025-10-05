import os
import mimetypes


def serve_file(self, client_socket, file_path):
    """Serve a file to the client"""
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = "application/octet-stream"

        # Send response
        response_headers = [
            "HTTP/1.1 200 OK",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(content)}",
            "Connection: close",
            "",
            "",
        ]

        header = "\r\n".join(response_headers).encode("utf-8")
        client_socket.sendall(header + content)
        print(f"✓ Served file: {os.path.basename(file_path)}")

    except Exception as e:
        print(f"✗ Error serving file: {e}")
        self.send_response(client_socket, 500, "Internal Server Error", "text/html")
