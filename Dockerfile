FROM cgr.dev/chainguard/python:3.11-dev@sha256:c7267ad0f84dd8b44fcea8962a0a97f44e719b703cf57321bff1576269a8043b

COPY discordbot.py config.py requirements.txt .

RUN pip install -r requirements.txt

ENV DEPLOYMENT_ENVIRONMENT=PROD
ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8080
ENV LOGLEVEL=WARNING
ENV SG_SERVER=sourcegraph.com

EXPOSE 8080

CMD ["discordbot.py"]