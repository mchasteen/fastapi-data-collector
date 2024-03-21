FROM python:3-slim-bullseye
LABEL authors="mchasteen"

# Create directory for the app user
RUN mkdir -p /home/app

# Create the app user
RUN addgroup --system app && adduser --system --group app

# create appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/code
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# Set envrionmental variables
ENV PTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1
ENV ENVRIONMENT prod

# Install System Depenencies
RUN apt-get update \
    && apt-get install -y ncat gcc libpq-dev \
    && apt-get clean

# Install Python Dependencies
RUN pip install --upgrade pip
RUN pip install -U setuptools
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy App
COPY . .

RUN chown -R app:app $APP_HOME

# Change to the app user
USER app

# Run Gunicon
# https://docs.gunicorn.org/en/stable/settings.html#accesslog
CMD gunicorn --bind 0.0.0.0:5000 main:app -k uvicorn.workers.UvicornWorker --log-level 'debug' --access-logfile '-' --capture-output