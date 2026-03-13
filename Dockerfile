FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WEB_PORT=8080 \
    TZ=UTC \
    PUID=1000 \
    PGID=1000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    ffmpeg \
    postgresql \
    postgresql-contrib \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ui-react /app/ui-react
RUN cd /app/ui-react && npm install && npm run build

COPY app /app/app
RUN mkdir -p /app/app/ui/static/app && cp -r /app/ui-react/dist/* /app/app/ui/static/app/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/config"]
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
