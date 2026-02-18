from sqlalchemy import create_engine, Column, Integer, Float, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import sqlalchemy

engine = create_engine("sqlite:///expenses.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    date = Column(Date, default=datetime.today)

Base.metadata.create_all(engine)