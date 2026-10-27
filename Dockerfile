# Cutline в контейнере: python + ffmpeg, данные в томе /data
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    OPEN_BROWSER=0 \
    USE_WAITRESS=1 \
    CUTLINE_DATA_DIR=/data \
    HF_HOME=/data/hf

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY req.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r req.txt

COPY . .

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://127.0.0.1:5000/health || exit 1

CMD ["python", "run.py"]
