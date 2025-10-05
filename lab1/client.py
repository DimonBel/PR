import socket
import sys
from urllib.parse import urlparse
import os


class HTTPClient:
    def __init__(self):
        self.socket = None

    def fetch(self, url, output_file=None):
        """Fetch a resource from the given URL"""
        # Parse URL
        parsed = urlparse(url)

        # Default values
        scheme = parsed.scheme or "http"
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path or "/"

        if not host:
            raise ValueError("Invalid URL: no host specified")

        if scheme != "http":
            raise ValueError("Only HTTP protocol is supported")

        print(f"Connecting to {host}:{port}")

        # Create socket and connect
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))

        # Build HTTP request
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}\r\n"
        request += "User-Agent: Python-HTTP-Client/1.0\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"

        print(f"Sending request:\n{request}")

        # Send request
        self.socket.sendall(request.encode("utf-8"))

        # Receive response
        response_data = b""
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            response_data += chunk

        self.socket.close()

        # Parse response
        response_str = response_data.decode("utf-8", errors="ignore")

        # Split headers and body
        if "\r\n\r\n" in response_str:
            headers_part, body_part = response_str.split("\r\n\r\n", 1)
        else:
            headers_part = response_str
            body_part = ""

        # Parse status line
        lines = headers_part.split("\r\n")
        status_line = lines[0]

        print(f"\nResponse status: {status_line}")
        print(f"\nHeaders:")
        for line in lines[1:]:
            if line:
                print(f"  {line}")

        # Extract status code
        status_parts = status_line.split()
        status_code = int(status_parts[1]) if len(status_parts) > 1 else 0

        print(f"\nStatus code: {status_code}")
        print(f"Body length: {len(body_part)} bytes")
        import os

        # Сохраняем тело в файл
        if output_file:
            # Если передан путь к папке, добавляем имя файла из URL
            if os.path.isdir(output_file):
                filename = os.path.basename(path)
                if not filename:
                    filename = "output.bin"  # имя по умолчанию
                output_file = os.path.join(output_file, filename)

            # Получаем тело из сырых байт
            body_start = response_data.find(b"\r\n\r\n") + 4
            body_bytes = response_data[body_start:]

            # Создаём папки если их нет
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, "wb") as f:
                f.write(body_bytes)
            print(f"\nSaved to: {output_file}")

        # Save or display body
        if output_file:
            # For binary files, we need to get the body from raw response_data
            body_start = response_data.find(b"\r\n\r\n") + 4
            body_bytes = response_data[body_start:]

            with open(output_file, "wb") as f:
                f.write(body_bytes)
            print(f"\nSaved to: {output_file}")
        else:
            # Display body (for text content)
            print(f"\nBody:\n{'-' * 60}")
            if len(body_part) > 1000:
                print(body_part[:1000])
                print(
                    f"\n... (truncated, showing first 1000 chars of {len(body_part)})"
                )
            else:
                print(body_part)
            print("-" * 60)

        return status_code, headers_part, body_part


def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <URL> [output_file_path]")
        print("\nExamples:")
        print("  python client.py http://localhost:8080/")
        print("  python client.py http://localhost:8080/test.txt")
        print(
            "  python client.py http://localhost:8080/image.png /home/user/output/image.png"
        )
        print("\nTask 4: Browse friend's server:")
        print("  python client.py http://192.168.1.100:8080/")
        sys.exit(1)

    url = sys.argv[1]
    output_file_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        client = HTTPClient()
        client.fetch(url, output_file_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
