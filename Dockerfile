# Python image to use.
FROM python:3.7-alpine

RUN apk add binutils libc-dev gcc libffi-dev openssl-dev build-base

# Set the working directory to /app
WORKDIR /app

# copy the requirements file used for dependencies
COPY requirements.txt .
ENV CRYPTOGRAPHY_DONT_BUILD_RUST 1

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the working directory contents into the container at /app
COPY src .
ARG COMMIT_SHA=62a729a3518b309fb09a637c0ac36f41eff66cdc
ADD https://raw.githubusercontent.com/InfuseAI/primehub/$COMMIT_SHA/chart/scripts/jupyterhub/config/primehub_utils.py .

ENV PORT 443
ENV WORKERS_PER_CORE 1
ENV WEB_CONCURRENCY 1

# Run app.py when the container launches
ENTRYPOINT gunicorn -w ${WORKERS_PER_CORE} --threads ${WEB_CONCURRENCY} -b 0.0.0.0:${PORT} --certfile=./ssl/cert.pem --keyfile=./ssl/key.pem main:app
