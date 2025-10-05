import socket
import os
import sys
import mimetypes
from pathlib import Path
from urllib.parse import unquote
from serve_directory import serve_directory
from send_404 import send_404
from serve_file import serve_file
from handle_request import handle_request
from send_response import send_response
from HTTPServer import HTTPServer


def main():
    if len(sys.argv) < 2:
        print("Usage: python server.py <directory> [port]")
        print("Example: python server.py . 8080")
        print("\nIf the port is already in use, the server will automatically")
        print("find the next available port.")
        sys.exit(1)

    directory = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1111

    try:
        server = HTTPServer(directory, port=port, auto_port=True)
        server.start()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
