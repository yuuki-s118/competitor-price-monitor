from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全 ORM モデルの共通ベース。Alembic の autogenerate はこれを見に来る。"""
