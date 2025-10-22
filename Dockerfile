FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Graphviz for generating the ERD
RUN apt-get update && apt-get install -y graphviz

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed for PostgreSQL
RUN apt-get update && apt-get install -y gcc libpq-dev

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/

# Install the Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . /app/

RUN python manage.py collectstatic --noinput