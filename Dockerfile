FROM python:3.11-slim@sha256:7d28177da146154adb077f7d71e21fdb9a7696128a7353b7db4cbb40c6e2d0ac

COPY discordbot.py config.py requirements.txt . 

RUN pip install -r requirements.txt
 
ENV HTTP_PORT=8080
ENV HTTP_HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "discordbot.py"]