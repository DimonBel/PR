import socket
import os
import sys
import mimetypes
from pathlib import Path
from urllib.parse import unquote


class HTTPServer:
    def __init__(self, directory, host='0.0.0.0', port=8080, auto_port=True):
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
        raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts}")
    
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
                print(f"Port {self.port} is already in use, searching for available port...")
                self.port = self.find_available_port(self.port + 1)
                self.socket.close()
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind((self.host, self.port))
                bind_successful = True
                print(f"✓ Found available port: {self.port}")
            else:
                raise RuntimeError(f"Port {self.port} is already in use. Use a different port or enable auto_port.") from e
        
        if not bind_successful:
            raise RuntimeError(f"Failed to bind to port {self.port}")
        
        self.socket.listen(5)
        
        print(f"\n{'='*60}")
        print(f"🚀 Server started on http://{self.host}:{self.port}")
        print(f"📁 Serving files from: {self.directory}")
        if self.port != original_port:
            print(f"⚠️  Note: Port {original_port} was in use, using {self.port} instead")
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
    
    def handle_request(self, client_socket):
        """Handle a single HTTP request"""
        try:
            # Receive the request
            request = client_socket.recv(4096).decode('utf-8')
            
            if not request:
                return
            
            # Parse the request line
            lines = request.split('\r\n')
            request_line = lines[0]
            print(f"Request: {request_line}")
            
            # Parse method, path, and version
            parts = request_line.split()
            if len(parts) < 2:
                self.send_response(client_socket, 400, "Bad Request", "text/html")
                return
            
            method = parts[0]
            path = unquote(parts[1])  # Decode URL encoding
            
            if method != 'GET':
                self.send_response(client_socket, 405, "Method Not Allowed", "text/html")
                return
            
            # Remove leading slash and resolve path
            if path.startswith('/'):
                path = path[1:]
            
            # Prevent directory traversal attacks
            full_path = os.path.normpath(os.path.join(self.directory, path))
            if not full_path.startswith(self.directory):
                self.send_response(client_socket, 403, "Forbidden", "text/html")
                return
            
            # If path is empty, serve the root directory
            if not path or path == '':
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
    
    def serve_file(self, client_socket, file_path):
        """Serve a file to the client"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # Send response
            response_headers = [
                'HTTP/1.1 200 OK',
                f'Content-Type: {content_type}',
                f'Content-Length: {len(content)}',
                'Connection: close',
                '',
                ''
            ]
            
            header = '\r\n'.join(response_headers).encode('utf-8')
            client_socket.sendall(header + content)
            print(f"✓ Served file: {os.path.basename(file_path)}")
        
        except Exception as e:
            print(f"✗ Error serving file: {e}")
            self.send_response(client_socket, 500, "Internal Server Error", "text/html")
    
    def serve_directory(self, client_socket, dir_path, url_path):
        """Serve a directory listing as HTML"""
        try:
            entries = os.listdir(dir_path)
            entries.sort()
            
            # Generate HTML directory listing
            html = [
                '<!DOCTYPE html>',
                '<html>',
                '<head>',
                '<meta charset="utf-8">',
                f'<title>Directory listing for /{url_path}</title>',
                '<style>',
                'body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }',
                '.container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
                'h1 { color: #333; margin-top: 0; }',
                'ul { list-style: none; padding: 0; }',
                'li { padding: 12px; border-bottom: 1px solid #eee; transition: background 0.2s; }',
                'li:hover { background: #f9f9f9; }',
                'a { text-decoration: none; color: #0066cc; }',
                'a:hover { text-decoration: underline; }',
                '.dir { font-weight: bold; color: #d97706; }',
                '.dir:before { content: "📁 "; }',
                '.file:before { content: "📄 "; }',
                '.parent:before { content: "⬆️ "; }',
                'footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }',
                '</style>',
                '</head>',
                '<body>',
                '<div class="container">',
                f'<h1>📂 Directory listing for /{url_path}</h1>',
                '<ul>'
            ]
            
            # Add parent directory link if not root
            if url_path:
                parent = '/'.join(url_path.rstrip('/').split('/')[:-1])
                html.append(f'<li class="parent"><a href="/{parent}">Parent Directory</a></li>')
            
            # Add entries
            for entry in entries:
                entry_path = os.path.join(dir_path, entry)
                url_entry = f"{url_path}/{entry}" if url_path else entry
                
                if os.path.isdir(entry_path):
                    html.append(f'<li class="dir"><a href="/{url_entry}/">{entry}/</a></li>')
                else:
                    html.append(f'<li class="file"><a href="/{url_entry}">{entry}</a></li>')
            
            html.extend([
                '</ul>',
                '<footer>',
                f'<em>Python HTTP File Server - Port {self.port}</em>',
                '</footer>',
                '</div>',
                '</body>',
                '</html>'
            ])
            
            content = '\n'.join(html).encode('utf-8')
            
            # Send response
            response_headers = [
                'HTTP/1.1 200 OK',
                'Content-Type: text/html; charset=utf-8',
                f'Content-Length: {len(content)}',
                'Connection: close',
                '',
                ''
            ]
            
            header = '\r\n'.join(response_headers).encode('utf-8')
            client_socket.sendall(header + content)
            print(f"✓ Served directory: {os.path.basename(dir_path) or 'root'}")
        
        except Exception as e:
            print(f"✗ Error serving directory: {e}")
            self.send_response(client_socket, 500, "Internal Server Error", "text/html")
    
    def send_404(self, client_socket, path):
        """Send 404 Not Found response"""
        content = f'''<!DOCTYPE html>
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
</html>'''
        
        content_bytes = content.encode('utf-8')
        response_headers = [
            'HTTP/1.1 404 Not Found',
            'Content-Type: text/html; charset=utf-8',
            f'Content-Length: {len(content_bytes)}',
            'Connection: close',
            '',
            ''
        ]
        
        header = '\r\n'.join(response_headers).encode('utf-8')
        client_socket.sendall(header + content_bytes)
        print(f"✗ 404 Not Found: {path}")
    
    def send_response(self, client_socket, status_code, status_text, content_type):
        """Send a simple HTTP response"""
        content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{status_code} {status_text}</title>
</head>
<body>
    <h1>{status_code} {status_text}</h1>
</body>
</html>'''
        
        content_bytes = content.encode('utf-8')
        response_headers = [
            f'HTTP/1.1 {status_code} {status_text}',
            f'Content-Type: {content_type}; charset=utf-8',
            f'Content-Length: {len(content_bytes)}',
            'Connection: close',
            '',
            ''
        ]
        
        header = '\r\n'.join(response_headers).encode('utf-8')
        client_socket.sendall(header + content_bytes)


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


if __name__ == '__main__':
    main()
