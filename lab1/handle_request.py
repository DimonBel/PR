import os


def handle_request(self, client_socket):
    """Handle a single HTTP request"""
    try:
        # Receive the request
        request = client_socket.recv(4096).decode("utf-8")

        if not request:
            return

        # Parse the request line
        lines = request.split("\r\n")
        request_line = lines[0]
        print(f"Request: {request_line}")

        # Parse method, path, and version
        parts = request_line.split()
        if len(parts) < 2:
            self.send_response(client_socket, 400, "Bad Request", "text/html")
            return

        method = parts[0]
        path = unquote(parts[1])  # Decode URL encoding

        if method != "GET":
            self.send_response(client_socket, 405, "Method Not Allowed", "text/html")
            return

        # Remove leading slash and resolve path
        if path.startswith("/"):
            path = path[1:]

        # Prevent directory traversal attacks
        full_path = os.path.normpath(os.path.join(self.directory, path))
        if not full_path.startswith(self.directory):
            self.send_response(client_socket, 403, "Forbidden", "text/html")
            return

        # If path is empty, serve the root directory
        if not path or path == "":
            full_path = self.directory

        # Check if path exists
        if not os.path.exists(full_path):
            self.send_404(client_socket, path)
            return

        # Handle directories
        if os.path.isdir(full_path):
            self.serve_directory(client_socket, full_path, path)
        else:
            self.serve_file(client_socket, full_path)

    except Exception as e:
        print(f"Error handling request: {e}")
        self.send_response(client_socket, 500, "Internal Server Error", "text/html")
    finally:
        client_socket.close()
