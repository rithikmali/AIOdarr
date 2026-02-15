FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Install dependencies (without lockfile for simpler builds)
RUN uv sync --no-dev

# Create non-root user
RUN useradd -m -u 1000 aiodarr && \
    chown -R aiodarr:aiodarr /app

USER aiodarr

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]
