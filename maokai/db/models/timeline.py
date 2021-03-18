from sqlalchemy import Column, Integer, String, ForeignKey
from ..common import Base


class TimelineParticipant(Base):
    __tablename__ = 'timeline_participants'

    game_id = Column(Integer, ForeignKey('matches.game_id', ondelete='CASCADE'), primary_key=True)
    timestamp = Column(Integer, primary_key=True)
    participant_id = Column(String, primary_key=True)

    current_gold = Column(Integer)
    total_gold = Column(Integer)
    level = Column(Integer)
    xp = Column(Integer)
    minions_killed = Column(Integer)
    jungle_minions_killed = Column(Integer)
    dominion_score = Column(Integer)
    team_score = Column(Integer)
    position_x = Column(Integer)
    position_y = Column(Integer)


class TimelineEvents(Base):
    __tablename__ = 'timeline_events'

    game_id = Column(Integer, ForeignKey('matches.game_id', ondelete='CASCADE'), primary_key=True)
    timestamp = Column(Integer, primary_key=True)
    participant_id = Column(String, primary_key=True)
    type = Column(String, primary_key=True)
    sequence = Column(Integer, primary_key=True)

    skill_slot = Column(String)
    level_up_type = Column(String)
    item_id = Column(String)
    ward_type = Column(String)
    creator_id = Column(String)
    killer_id = Column(String)
    victim_id = Column(String)
    assisting_participant_ids = Column(String)
    position_x = Column(String)
    position_y = Column(String)
    monster_type = Column(String)
    after_id = Column(String)
    before_id = Column(String)
    team_id = Column(String)
    building_type = Column(String)
    lane_type = Column(String)
    tower_type = Column(String)
    monster_sub_type = Column(String)