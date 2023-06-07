FROM python:3.8-slim

COPY discordbot.py config.py requirements.txt . 

RUN pip install -r requirements.txt
 
CMD ["python", "discordbot.py"]