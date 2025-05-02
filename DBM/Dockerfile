FROM python:3.12-slim


RUN apt-get update && apt-get install -y 
gcc 
libpq-dev 
libevent-dev 
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["gunicorn", "--worker-class", "gevent", "--workers", "2", "--timeout", "120", "--bind", "0.0.0.0:5000", "app:app"]