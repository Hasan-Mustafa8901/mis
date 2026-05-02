FROM python:3.11-slim

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
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
