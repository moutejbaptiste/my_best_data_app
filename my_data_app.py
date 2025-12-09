# db.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, MetaData, Table
from sqlalchemy.orm import sessionmaker
import pandas as pd

DB_URI = "sqlite:///coinafrica.db"

engine = create_engine(DB_URI, echo=False)
metadata = MetaData()

listings = Table(
    "listings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("category", String(100)),   # e.g., vetements-homme
    Column("type", String(200)),       # V1: type clothes/shoes
    Column("raw_price", String(100)),
    Column("price", Float, nullable=True),
    Column("address", String(255)),
    Column("image_link", Text),
    Column("source_url", Text)
)

def init_db():
    metadata.create_all(engine)

def insert_rows(df: pd.DataFrame):
    df.to_sql("listings", engine, if_exists="append", index=False)

def read_all():
    return pd.read_sql_table("listings", engine)
