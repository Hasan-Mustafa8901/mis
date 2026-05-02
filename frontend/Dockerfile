FROM python:3.11-slim

# Install system dependencies if required for NiceGUI/Selenium (like libglib2.0-0, libnss3, etc.)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy project files
COPY . .

# Expose the application port
EXPOSE 3000

# Run the application
CMD ["uv", "run", "python", "main.py"]
