import socket

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

database_url = settings.sqlalchemy_database_url
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
if database_url.startswith("postgresql"):
    connect_args["connect_timeout"] = 10
    database_host = make_url(database_url).host
    if database_host:
        try:
            ipv4_addresses = socket.getaddrinfo(database_host, None, socket.AF_INET, socket.SOCK_STREAM)
        except socket.gaierror:
            ipv4_addresses = []
        if ipv4_addresses:
            connect_args["hostaddr"] = ipv4_addresses[0][4][0]
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
