FROM python:3.14


# required for psycopg2
RUN apt install -y libpq-dev
