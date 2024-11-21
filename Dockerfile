# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements  file to leverage Docker cache
COPY ./requirements.txt ./

# Install any needed packages specified in requirements.txt and cron
RUN apt-get update && \
    apt-get install -y cron && \
    pip install -r requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY ./cronfile ./entrypoint.sh ./
RUN chmod +x ./entrypoint.sh
COPY ./src ./src

# Run the command on container startup
ENTRYPOINT ["/app/entrypoint.sh"]
