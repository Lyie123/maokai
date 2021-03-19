from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey
from ..common import Base
from datetime import datetime


class League(Base):
    __tablename__ = 'league'

    league_id = Column(String, primary_key=True)
    tier = Column(String)
    name = Column(String)
    queue = Column(String)


class LeagueHistory(Base):
    __tablename__ = 'league_history'

    summoner_id = Column(String, primary_key=True)
    league_id = Column(String, primary_key=True)
    wins = Column(Integer, primary_key=True)
    losses = Column(Integer, primary_key=True)

    event_time = Column(DateTime, default=datetime.utcnow)
    league_points = Column(Integer)