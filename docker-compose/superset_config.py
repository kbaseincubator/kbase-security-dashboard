# required for startup
SECRET_KEY = "ThisIsAFakeKeyForLocalTestingDoNotUseItInProductionOrYoureADoof"

# These are set in the docker-compose.yaml file
SQLALCHEMY_DATABASE_URI = "postgresql://superset:superset@postgres:5432/superset_db"
