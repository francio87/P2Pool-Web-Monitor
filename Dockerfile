FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1
ENV P2POOL_DIR=/p2pool-data
ENV DATA_API_DIR=/p2pool-data
ENV OUTPUT=/output/index.html
ENV HTTP_PORT=8080
ENV P2POOL_VERSION_CHECK=true

WORKDIR /app

COPY src /app/src
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=40s \
  CMD python3 /app/src/container_healthcheck.py --output-dir /output --max-age 120 --http-url http://127.0.0.1:8080/index.html

CMD ["/app/docker-entrypoint.sh"]
