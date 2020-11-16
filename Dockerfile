FROM ubuntu:bionic
MAINTAINER Barry Moore "moore0557@gmail.com"
RUN apt update
RUN apt upgrade -y --no-install-recommends
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-dev \
    python3-pip python3-setuptools python3-wheel build-essential \
    --no-install-recommends
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY app.py requirements.txt /app/
RUN mkdir /app/assets
COPY assets/table.css /app/assets/table.css
RUN pip3 install -r requirements.txt
EXPOSE 5000
CMD ["uwsgi", "--http", ":5000", "--module", "app:server", "--uid", "nobody", "--master"]
