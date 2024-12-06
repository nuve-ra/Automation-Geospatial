import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.database import Base

@pytest.fixture(scope="session")
def engine():
    return create_engine("postgresql+psycopg://postgres:postgres@localhost/test_karnataka_geodb")

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, tables):
    """Returns a sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
