FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1
ENV P2POOL_DIR=/p2pool-data
ENV DATA_API_DIR=/p2pool-data
ENV OUTPUT=/output/index.html
ENV HTTP_PORT=8080

WORKDIR /app

COPY src /app/src
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8080

CMD ["/app/docker-entrypoint.sh"]
