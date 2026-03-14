FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

ENV PYTHONPATH="/app:/app/src"

CMD ["python", "src/bot.py"]
