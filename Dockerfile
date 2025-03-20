# Python image to use.
FROM python:3.10-alpine

RUN apk add binutils libc-dev gcc libffi-dev openssl-dev build-base

# Set the working directory to /app
WORKDIR /app

# copy the requirements file used for dependencies
COPY requirements.txt .
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the working directory contents into the container at /app
COPY primehub_admission/ ./primehub_admission/
COPY main.py main.py

ENV PORT=443
ENV WORKERS_PER_CORE=1
ENV WEB_CONCURRENCY=1
ENV FLASK_DEBUG=0

# Run app.py when the container launches
ENTRYPOINT gunicorn -e FLASK_DEBUG=${FLASK_DEBUG} -w ${WORKERS_PER_CORE} --threads ${WEB_CONCURRENCY} -b 0.0.0.0:${PORT} --certfile=./ssl/cert.pem --keyfile=./ssl/key.pem main:app
