FROM python:3.12-slim-bookworm

ENV LOCAL_SERVER=""

WORKDIR /app

COPY ./app /app

RUN apt update

RUN apt install libicu-dev -y

RUN pip install --no-cache-dir --upgrade -r /app/r.txt

EXPOSE 8010

CMD ["fastapi", "run", "main.py", "--port", "8010", "--no-reload", "--proxy-headers" ]