FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.txt

COPY . .

EXPOSE 8000

RUN chmod +x /app/devops/docker-entrypoint.sh \
    && chmod +x /app/devops/run_app.sh

ENTRYPOINT ["/app/devops/docker-entrypoint.sh"]
CMD ["/app/devops/run_app.sh"]

