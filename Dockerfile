FROM python:3.12-slim AS base

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

COPY . .

FROM base

RUN python manage.py migrate && \
    export DJANGO_SUPERUSER_PASSWORD=admin && \
    python manage.py createsuperuser --username admin --email admin@gatech.edu --noinput

RUN python manage.py populate_pokemon

EXPOSE 8000

ENTRYPOINT [ "python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload" ]
