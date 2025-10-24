# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

WORKDIR /app

COPY server.py .

RUN mkdir -p /srv/files

RUN chmod +x server.py 

EXPOSE 2222

CMD ["python", "server.py", "/srv/files", "3333"]