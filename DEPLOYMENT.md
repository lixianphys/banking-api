# SimpleBank API Deployment Guide

This guide explains how to deploy the SimpleBank API using Docker and Kubernetes.

## Prerequisites

- Docker and Docker Compose

## Docker Deployment

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t simplebank-api:latest .

# Run the container
docker run -p 8000:8000 -e API_KEY=your_api_key simplebank-api:latest
```

### Using Docker Compose

```bash
# Start the application with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the application
docker-compose down
```
