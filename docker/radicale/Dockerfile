FROM python:3.13-slim

# Install Radicale
RUN pip install --no-cache-dir radicale

# Create necessary directories
RUN mkdir -p /data/collections /config

# Copy configuration
COPY config /config/config
COPY users /config/users

# Expose port
EXPOSE 5232

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5232').read()" || exit 1

# Run Radicale
CMD ["radicale", "--config", "/config/config"]
