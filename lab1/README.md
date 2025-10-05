# HTTP File Server with TCP Sockets

### Course: Computer Networks

### Author: Belih Dmitrii

---

## Theory

&emsp;&emsp;&emsp; An HTTP server is a software application that handles HTTP requests from clients (typically web browsers) and serves responses, usually in the form of web pages, files, or data. The Hypertext Transfer Protocol (HTTP) is the foundation of data communication on the World Wide Web. It operates on a client-server model where clients send requests to servers, and servers respond with the requested resources.

&emsp;&emsp;&emsp; TCP sockets provide a reliable, connection-oriented communication channel between two endpoints. In the context of HTTP, TCP ensures that data packets are delivered in order and without loss, which is crucial for web communication. The server listens on a specific port (commonly 80 for HTTP) for incoming connections, accepts them, processes the requests, and sends back responses.

&emsp;&emsp;&emsp; File serving involves reading files from the server's filesystem and transmitting them over the network. This requires proper handling of different file types, MIME types, and HTTP headers to ensure correct interpretation by clients. Directory listing generates HTML representations of directory contents, allowing users to navigate through the server's file structure.

## Objectives:

1. Understand the fundamentals of HTTP protocol and TCP socket programming.

2. Implement a basic HTTP file server that serves static files from a specified directory.

3. Handle different HTTP methods, status codes, and content types.

4. Implement security measures to prevent directory traversal attacks.

5. Create an HTTP client for testing the server functionality.

6. Support directory browsing with generated HTML listings.

7. Handle various file types including HTML, PNG, and PDF.

8. Ensure the server can be restarted without "Address already in use" errors.

9. Deploy the server using Docker for containerized execution.

10. Enable browsing files on remote servers within the local network.

## Implementation description

### `HTTPServer` Class Description

The `HTTPServer` class represents a simple HTTP file server implemented using TCP sockets. It serves static files from a specified directory and handles HTTP GET requests.

#### **Fields**

**Private Fields**

- `directory` (str): The root directory from which files are served.
- `host` (str): The host address to bind the server (default: '0.0.0.0').
- `port` (int): The port number to listen on.
- `auto_port` (bool): Whether to automatically find an available port if the specified one is in use.
- `socket` (socket): The TCP socket object for server operations.

#### **Methods**

##### 1. `__init__(self, directory, host='0.0.0.0', port=8080, auto_port=True)`

Initializes the HTTP server with the specified directory, host, port, and auto-port settings.

**Parameters:**

- `directory` (str): Path to the directory to serve files from.
- `host` (str): Host address to bind to (default: '0.0.0.0').
- `port` (int): Port number to listen on (default: 8080).
- `auto_port` (bool): Enable automatic port selection if port is busy (default: True).

##### 2. `find_available_port(self, start_port, max_attempts=100)`

Finds an available port starting from the specified port.

**Parameters:**

- `start_port` (int): The starting port number to check.
- `max_attempts` (int): Maximum number of ports to try (default: 100).

**Returns:**

- `int`: The first available port number.

##### 3. `start(self)`

Starts the HTTP server, binds to the specified host and port, and begins accepting connections.

##### 4. `handle_request(self, client_socket)`

Handles a single HTTP request from a client.

**Parameters:**

- `client_socket` (socket): The client socket connection.

**Logic:**

1. Receive the HTTP request.
2. Parse the request line to extract method, path, and version.
3. Validate the request (only GET method is supported).
4. Decode and validate the requested path.
5. Prevent directory traversal attacks.
6. Check if the path exists.
7. Serve directories or files accordingly.
8. Handle errors and send appropriate HTTP responses.

##### 5. `serve_file(self, client_socket, file_path)`

Serves a file to the client with appropriate HTTP headers.

**Parameters:**

- `client_socket` (socket): The client socket connection.
- `file_path` (str): Path to the file to serve.

**Logic:**

1. Read the file content in binary mode.
2. Determine the MIME type using `mimetypes.guess_type()`.
3. Send HTTP 200 OK response with proper headers.
4. Send the file content.

##### 6. `serve_directory(self, client_socket, dir_path, url_path)`

Generates and serves an HTML directory listing.

**Parameters:**

- `client_socket` (socket): The client socket connection.
- `dir_path` (str): Path to the directory to list.
- `url_path` (str): The URL path corresponding to the directory.

**Logic:**

1. List directory entries and sort them.
2. Generate HTML with CSS styling for the directory listing.
3. Include parent directory link if not at root.
4. Create links for subdirectories and files.
5. Send HTTP 200 OK response with the HTML content.

##### 7. `send_404(self, client_socket, path)`

Sends an HTTP 404 Not Found response with a custom HTML page.

**Parameters:**

- `client_socket` (socket): The client socket connection.
- `path` (str): The requested path that was not found.

##### 8. `send_response(self, client_socket, status_code, status_text, content_type)`

Sends a simple HTTP response with the specified status.

**Parameters:**

- `client_socket` (socket): The client socket connection.
- `status_code` (int): HTTP status code.
- `status_text` (str): HTTP status text.
- `content_type` (str): Content type for the response.

### `HTTPClient` Class Description

The `HTTPClient` class implements a simple HTTP client using TCP sockets for testing the server.

#### **Fields**

**Private Fields**

- `socket` (socket): The TCP socket object for client operations.

#### **Methods**

##### 1. `fetch(self, url, output_file=None)`

Fetches a resource from the specified URL.

**Parameters:**

- `url` (str): The URL to fetch.
- `output_file` (str, optional): File path to save the response body.

**Returns:**

- `tuple`: (status_code, headers, body)

**Logic:**

1. Parse the URL to extract host, port, and path.
2. Create a TCP socket and connect to the server.
3. Build and send an HTTP GET request.
4. Receive the complete HTTP response.
5. Parse the response to separate headers and body.
6. Display response information.
7. Save to file if output_file is specified, otherwise display the body.

### Docker Deployment

The project includes Docker configuration for containerized deployment:

#### **Dockerfile**

- Uses Python 3.11 slim base image.
- Copies server and client scripts.
- Creates sample files for demonstration.
- Exposes port 2222.
- Runs the server by default.

#### **docker-compose.yml**

- Defines three services: main server, friend's server, and client.
- Uses custom network with unique subnet.
- Includes health checks and volume mounts.
- Enables inter-container communication.

#### **start-servers.sh**

- Shell script to start the Docker services.
- Detects local network IP for network access.
- Displays URLs for local and network access.

## Usage Examples

### Running the Server

```bash
# Basic usage
python server.py /path/to/directory

# With custom port
python server.py /path/to/directory 8080
```

### Running the Client

```bash
# Fetch HTML content (displayed in console)
python client.py http://localhost:8080/index.html

# Download binary file
python client.py http://localhost:8080/image.png output.png
```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Conclusions / Screenshots / Results

This laboratory work provided hands-on experience with low-level network programming using TCP sockets and HTTP protocol implementation. By building a complete HTTP file server from scratch, I gained a deep understanding of how web servers work at the socket level.

Key learnings include:

- TCP socket programming for reliable network communication
- HTTP request/response parsing and generation
- MIME type handling for different file formats
- Security considerations like preventing directory traversal attacks
- Error handling and HTTP status codes
- Containerization with Docker for deployment
- Network configuration for local network access

The implementation successfully handles static file serving, directory browsing, and supports multiple file types. The Docker setup enables easy deployment and testing in containerized environments.

![Server running in terminal](img/img3.jpg)
_Server successfully serving files from the specified directory_

![Client running in terminal](img/img2.jpg)

![Client running in terminal](img/img1.jpg)
_Client takes successfully serving files from the specified directory_

![UI of server ](img/UI.jpg)
_UI of server_

![PDF open in server](img/PDF.jpg)
_PDF open in server_

![txt open in server](img/txt.jpg)
_txt open in server_

## References

- https://tools.ietf.org/html/rfc7230 (HTTP/1.1 Message Syntax and Routing)
- https://tools.ietf.org/html/rfc7231 (HTTP/1.1 Semantics and Content)
- https://docs.python.org/3/library/socket.html (Python Socket Library)
- https://docs.docker.com/compose/ (Docker Compose Documentation)
