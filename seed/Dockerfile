FROM python:3.11-slim
WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -e /app/shared

COPY seed /app/seed

CMD ["python", "-m", "seed.load_seed"]
