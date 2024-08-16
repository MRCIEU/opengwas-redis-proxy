FROM python:3.12-alpine

COPY ./requirements.txt /requirements.txt
RUN python -m pip install -r /requirements.txt

COPY . /redis-proxy
WORKDIR /redis-proxy

ENTRYPOINT ["sh", "gunicorn.sh"]
