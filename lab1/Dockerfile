# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy server and client Python files
COPY server.py .
COPY client.py .

# Create directory for serving files
RUN mkdir -p /srv/files

# Create some sample files for demonstration
RUN echo "Hello from HTTP Server!" > /srv/files/hello.txt && \
    echo "<!DOCTYPE html><html><head><title>Sample</title></head><body><h1>Welcome!</h1><p>This is a sample HTML file.</p></body></html>" > /srv/files/index.html && \
    mkdir -p /srv/files/docs && \
    echo "Documentation file" > /srv/files/docs/readme.txt && \
    mkdir -p /srv/files/images

# Make scripts executable
RUN chmod +x server.py client.py

# Expose port 
EXPOSE 2222

# Default command - start the server
CMD ["python", "server.py", "/srv/files", "2222"]