FROM python:3.13


# required for psycopg2
RUN apt install -y libpq-dev
