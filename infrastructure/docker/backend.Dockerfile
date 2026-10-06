FROM python:3.11-slim
WORKDIR /app
RUN useradd -m appuser
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY database ./database
COPY configs ./configs
COPY scripts ./scripts
RUN pip install --no-cache-dir .
RUN mkdir -p /app/artifacts /app/models && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "x_sentinel.main:app", "--host", "0.0.0.0", "--port", "8000"]
