import os


def serve_directory(self, client_socket, dir_path, url_path):
    """Serve a directory listing as HTML"""
    try:
        entries = os.listdir(dir_path)
        entries.sort()

        # Generate HTML directory listing
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

        # Add parent directory link if not root
        if url_path:
            parent = "/".join(url_path.rstrip("/").split("/")[:-1])
            html.append(
                f'<li class="parent"><a href="/{parent}">Parent Directory</a></li>'
            )

        # Add entries
        for entry in entries:
            entry_path = os.path.join(dir_path, entry)
            url_entry = f"{url_path}/{entry}" if url_path else entry

            if os.path.isdir(entry_path):
                html.append(
                    f'<li class="dir"><a href="/{url_entry}/">{entry}/</a></li>'
                )
            else:
                html.append(f'<li class="file"><a href="/{url_entry}">{entry}</a></li>')

        html.extend(
            [
                "</ul>",
                "<footer>",
                f"<em>Python HTTP File Server - Port {self.port}</em>",
                "</footer>",
                "</div>",
                "</body>",
                "</html>",
            ]
        )

        content = "\n".join(html).encode("utf-8")

        # Send response
        response_headers = [
            "HTTP/1.1 200 OK",
            "Content-Type: text/html; charset=utf-8",
            f"Content-Length: {len(content)}",
            "Connection: close",
            "",
            "",
        ]

        header = "\r\n".join(response_headers).encode("utf-8")
        client_socket.sendall(header + content)
        print(f"✓ Served directory: {os.path.basename(dir_path) or 'root'}")

    except Exception as e:
        print(f"✗ Error serving directory: {e}")
        self.send_response(client_socket, 500, "Internal Server Error", "text/html")
