FROM python:3.7-slim-stretch

RUN apt-get update && apt-get install -y git python3-dev gcc htop sudo \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade -r requirements.txt

COPY app app/
# COPY keyfile.json .
ENV WEB_CONCURRENCY=1
ENV PORT=8080

EXPOSE 8080

CMD uvicorn app.server:app --port $PORT --workers $WEB_CONCURRENCY --host 0.0.0.0
