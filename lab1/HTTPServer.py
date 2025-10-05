import socket
import os


class HTTPServer:
    def __init__(self, directory, host="0.0.0.0", port=8080, auto_port=True):
        self.directory = os.path.abspath(directory)
        self.host = host
        self.port = port
        self.auto_port = auto_port
        self.socket = None

        if not os.path.isdir(self.directory):
            raise ValueError(f"Directory '{directory}' does not exist")

    def find_available_port(self, start_port, max_attempts=100):
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            try:
                # Try to bind to the port
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

    def start(self):
        """Start the HTTP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Try to bind to the specified port
        original_port = self.port
        bind_successful = False

        try:
            self.socket.bind((self.host, self.port))
            bind_successful = True
        except OSError as e:
            if self.auto_port:
                print(
                    f"Port {self.port} is already in use, searching for available port..."
                )
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

        self.socket.listen(5)

        print(f"\n{'='*60}")
        print(f"🚀 Server started on http://{self.host}:{self.port}")
        print(f"📁 Serving files from: {self.directory}")
        if self.port != original_port:
            print(
                f"⚠️  Note: Port {original_port} was in use, using {self.port} instead"
            )
        print(f"{'='*60}")
        print("Press Ctrl+C to stop the server\n")

        try:
            while True:
                client_socket, client_address = self.socket.accept()
                print(f"Connection from {client_address}")
                self.handle_request(client_socket)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down server...")
        finally:
            self.socket.close()
            print("✓ Server stopped")
