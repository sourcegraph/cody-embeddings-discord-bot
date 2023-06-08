FROM python:3.11-slim

COPY discordbot.py config.py requirements.txt . 

RUN pip install -r requirements.txt
 
ENV HTTP_PORT=8080
ENV HTTP_HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "discordbot.py"]