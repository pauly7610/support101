from sqlalchemy import Column, Integer, String

from apps.backend.app.core.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Integer, default=0, nullable=False)  # 0 = False, 1 = True
    data_sale_optout = Column(Integer, default=0, nullable=False)  # 0 = False, 1 = True
