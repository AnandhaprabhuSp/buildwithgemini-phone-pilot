FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV AGENT_ENGINE_RESOURCE_NAME="projects/28275805489/locations/us-east1/reasoningEngines/8121175401683746816"
ENV AGENT_DIRECTORY="app"

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
