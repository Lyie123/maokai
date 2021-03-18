from sqlalchemy import Integer, String, Column, DateTime
from ..common import Base


class Summoner(Base):
    __tablename__ = 'summoner'

    account_id = Column(String, primary_key=True)

    summoner_id = Column(String)
    puuid = Column(String)
    summoner_name = Column(String)
    profile_icon_id = Column(Integer)
    revision_date = Column(DateTime)
    summoner_level = Column(Integer)