from ..api.riot import RiotApi, QueueType, logging

import pandas as pd
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError

from .models.views import v_summoner_matches, v_summoner_recently_played_champions
from .models.summoner import Summoner
from .models.match import Match
from .models.league import League, LeagueHistory
from .common import Base


class LeagueDB:
    def __init__(self, con: str, api_key: str):
        self.engine = create_engine(con)
        self.api = RiotApi(api_key)
        self.create_db_layout()

    def create_db_layout(self) -> None:
        Base.metadata.create_all(self.engine)
        self.create_static_data()
        self._create_views()

    def update_summoner(self, summoner_name: str, number_of_games: int = 100, champion_id: int = None,
                        season_id: str = None, patch: str = None, begin_time: datetime = None,
                        queue_id: int = None, get_timeline_data: bool = False) -> None:
        logging.info('update summoner: {0}'.format(summoner_name))
        with Session(self.engine) as session:
            try:
                # step 1: gather summoner data
                df_summoner = self.api.get_summoner(summoner_name=summoner_name)
                if df_summoner.empty:
                    logging.info('summoner with name {0} not found'.format(summoner_name))
                    return

                summoner = Summoner(**df_summoner.reset_index().iloc[0])
                session.merge(summoner)
                session.commit()

            except Exception as e:
                logging.error('error while gathering summoner data for summoner {0}'.format(summoner_name))
                logging.error(str(e))
                return

            try:
                # step 2: gather league information for summoner
                df_league_entries = self.api.get_league_entries_of_summoner(summoner_id=summoner.summoner_id)

                # check if league is already created
                for idx, entry in df_league_entries.reset_index().iterrows():
                    df_league = self.api.get_league(entry.league_id)['league']
                    session.merge(League(**df_league.reset_index().iloc[0]))
                    session.commit()

                    cols = ['summoner_id', 'league_id', 'league_points', 'wins', 'losses']
                    session.merge(LeagueHistory(**entry[cols]))
                    session.commit()

            except Exception as e:
                logging.error('error while gathering league data for summoner {0}'.format(summoner_name))
                logging.error(str(e))
                return

            try:
                # step 3: get match history of summoner
                matches = self.api.get_match_history(account_id=summoner.account_id, champion=champion_id,
                                                     endIndex=number_of_games, beginTime=begin_time, queue=queue_id)
                if matches.empty:
                    logging.info('no new matches for summoner {0}'.format(summoner_name))
                    return

                # check which matches are already stored in database
                query = select(Match).where(Match.game_id.in_(matches.game_id))
                db_matches = pd.read_sql(sql=query, con=session.bind)
                new_matches = matches[~matches.game_id.isin(db_matches.game_id)]

                # step 4 get match details of summoner
                logging.info('{0} out of {1} are new matches'.format(len(new_matches), len(matches)))
                for match in new_matches.game_id:
                    try:
                        details = self.api.get_match_details(match)
                        for name, table in details.items():
                            try:
                                table.to_sql(name=name, con=session.bind, if_exists='append')
                            except IntegrityError:
                                pass

                        if get_timeline_data:
                            timeline = self.api.get_timeline(match)
                            for name, table in timeline.items():
                                table = table.applymap(str)
                                table.to_sql(name=name, con=session.bind, if_exists='append')

                        logging.info('Merged {0} successfully'.format(match))
                    except Exception as e:
                        logging.error('error while gathering match details for game_id {0}'.format(match))
                        logging.error(str(e))
            except NoResultFound as e:
                logging.info('no new matches for summoner {0}'.format(summoner_name))
                pass
            except Exception as e:
                logging.error('error while gathering game_id data for summoner {0}'.format(summoner_name))
                logging.error(str(e))

    def _create_views(self) -> None:
        self.engine.execute(v_summoner_matches)
        self.engine.execute(v_summoner_recently_played_champions)

    def create_static_data(self) -> None:
        if not self.engine.has_table('leaderboard_flex') or not self.engine.has_table('leaderboard_solo'):
            logging.info('table "leaderboard_solo" and "leaderboard_flex" created')
            self._update_challenger_leaderboard()
        if not self.engine.has_table('champions'):
            logging.info('table "champions" created')
            self._update_champions()
        if not self.engine.has_table('queues'):
            logging.info('table "queues" created')
            self._update_queue_types()

    def _update_challenger_leaderboard(self) -> None:
        solo = self.api.get_challenger_leaderboard(QueueType.RANKED_SOLO)['league_entries']
        solo.to_sql(name='leaderboard_solo', con=self.engine, if_exists='replace')

        flex = self.api.get_challenger_leaderboard(QueueType.RANKED_FLEX)['league_entries']
        flex.to_sql(name='leaderboard_flex', con=self.engine, if_exists='replace')

    def _update_champions(self) -> None:
        champions = self.api.get_champion_data()
        champions.to_sql(name='champions', con=self.engine, if_exists='replace')

    def _update_queue_types(self) -> None:
        queues = self.api.get_queue_types()
        queues.to_sql(name='queues', con=self.engine, if_exists='replace')
