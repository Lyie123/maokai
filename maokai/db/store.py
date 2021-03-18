from datetime import datetime
import pandas as pd
from sqlalchemy.orm.exc import NoResultFound
from ..api.league import RiotApi, QueueType, logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models.summoner import Summoner
from .models.match import Match
from .common import Base


class LeagueDB:
    def __init__(self, con: str, api_key: str):
        self.engine = create_engine(con)
        self.Session = sessionmaker(bind=self.engine)
        self.api = RiotApi(api_key)
        self.create_db_layout()

    def create_db_layout(self) -> None:
        Base.metadata.create_all(self.engine)

    def update_summoner(self, summoner_name: str, number_of_games: int = 100, champion_id: int = None,
                        season_id: str = None, patch: str = None, begin_time: datetime = None,
                        queue_id: int = None) -> None:
        logging.info('update summoner: {0}'.format(summoner_name))
        session = self.Session()
        try:
            df_summoner = self.api.get_summoner(summoner_name=summoner_name)
            if df_summoner.empty:
                logging.info('summoner with name {0} not found'.format(summoner_name))
                return

            summoner = Summoner(**df_summoner.reset_index().iloc[0])
            session.merge(summoner)
            session.commit()

            try:
                matches = self.api.get_match_history(account_id=summoner.account_id, champion=champion_id,
                                                     endIndex=number_of_games, beginTime=begin_time, queue=queue_id)
                if matches.empty:
                    logging.info('no new matches for summoner {0}'.format(summoner_name))
                    return

                query = session.query(Match).filter(Match.game_id.in_([str(n) for n in matches.game_id.values]))
                matches_already_loaded = pd.read_sql(sql=query.statement, con=session.bind)
                if matches_already_loaded.empty:
                    new_matches = matches.game_id.values
                else:
                    new_matches = matches[~matches.game_id.isin(matches_already_loaded.game_id)].game_id.values

                logging.info('{0} out of {1} are new matches'.format(len(new_matches), len(matches)))
                for match in new_matches:
                    try:
                        details = self.api.get_match_details(match)
                        for name, table in details.items():
                            try:
                                table.to_sql(name=name, con=session.bind, if_exists='append')
                            except IntegrityError:
                                pass

                        timeline = self.api.get_timeline(match)
                        for name, table in timeline.items():
                            table = table.applymap(str)
                            table.to_sql(name=name, con=session.bind, if_exists='append')

                        logging.info('Merged {0} successfully'.format(match))
                    except Exception as e:
                        logging.error('error while gathering match details for game_id {0}'.format(match))
                        logging.error(str(e))
                        pass
            except NoResultFound as e:
                logging.info('no new matches for summoner {0}'.format(summoner_name))
                pass
            except Exception as e:
                logging.error('error while gathering game_id data for summoner {0}'.format(summoner_name))
                logging.error(str(e))

        except Exception as e:
            logging.error('error while gathering summoner data for summoner {0}'.format(summoner_name))
            logging.error(str(e))
            pass

    def update_static_data(self) -> None:
        self._update_challenger_leaderboard()
        print('leaderboards have been created')
        self._update_champions()
        print('champions have been created')
        self._update_queue_types()
        print('queues have been updated')

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
