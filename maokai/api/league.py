import requests
import pandas as pd
import re
import json
import logging  # https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
from collections import deque
from typing import Dict, Union
from time import sleep
from datetime import datetime
from enum import Enum


logging.basicConfig(filename='maokai.log', level=logging.INFO, format='%(asctime)s %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S')

regions = {
    'EUW': 'https://euw1.api.riotgames.com'
}

endpoints = {
    'summoner_v4': {
        'by_account': '{base_uri}/lol/summoner/v4/summoners/by-account/{encryptedAccountId}',
        'by_name': '{base_uri}/lol/summoner/v4/summoners/by-name/{summonerName}',
        'by_puuid': '{base_uri}/lol/summoner/v4/summoners/by-puuid/{encryptedPUUID}',
        'by_id': '{base_uri}/lol/summoner/v4/summoners/{encryptedSummonerId}'
    },
    'match_v4': {
        'list': '{base_uri}/lol/match/v4/matchlists/by-account/{encryptedAccountId}',
        'details': '{base_uri}/lol/match/v4/matches/{matchId}',
        'timeline': '{base_uri}/lol/match/v4/timelines/by-match/{matchId}'
    },
    'league_v4': {
        'challenger': '{base_uri}/lol/league/v4/challengerleagues/by-queue/{queue_type}',
        'grandmaster': '{base_uri}/lol/league/v4/grandmasterleagues/by-queue/{queue_type}',
        'master': '{base_uri}/lol/league/v4/masterleagues/by-queue/{queue_type}',
        'entries': '{base_uri}/lol/league/v4/entries/by-summoner/{encryptedSummonerId}',
        'league': '{base_uri}/lol/league/v4/leagues/{leagueId}'
    },
    'ddragon': {
        'champion': 'http://ddragon.leagueoflegends.com/cdn/{local}/data/en_US/champion.json',
        'version': 'https://ddragon.leagueoflegends.com/api/versions.json',
        'queues': 'http://static.developer.riotgames.com/docs/lol/queues.json'
    }
}

status_codes = {
    400: 'bad request',
    401: 'unauthorized',
    403: 'forbidden',
    404: 'data not found',
    405: 'method not allowed',
    415: 'unsupported media type',
    429: 'rate limit exceeded',
    500: 'internal server error',
    504: 'service unavaiable'
}


class QueueType(Enum):
    RANKED_SOLO = 'RANKED_SOLO_5x5'
    RANKED_FLEX = 'RANKED_FLEX_SR'


class RiotApi:
    def __init__(self, api_key: str, region: str = 'EUW') -> None:
        if region not in regions:
            raise ValueError('{region} is not a valid region'.format(region=region))

        self._base_uri = regions[region]
        self._key = api_key
        self._header = {
            'Origin': 'https://developer.riotgames.com',
            'X-Riot-Token': self._key
        }
        self._query_delay_time = 0.1
        self._version = self.get_latest_version()
        self._api_calls = deque(maxlen=100)

    @staticmethod
    def __snake_case(camel_case: str) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_case).lower()

    def __post_query(self, query: str) -> Dict:
        sleep(self._query_delay_time)
        r = requests.get(query, headers=self._header)

        # query was succesful 
        if r.status_code == 200:
            self._api_calls.append('{time}: {query}'.format(time=datetime.now(), query=query))
            return r.json()

        # something went wrong...
        elif r.status_code in (400, 401, 403, 404, 405, 415, 500, 503, 504):
            raise Exception('{0} {1}: {2}'.format(r.status_code, status_codes[r.status_code], query))

        # bad request
        elif r.status_code == 429:
            logging.warning('Rate limit exceeded. Sleep 121 seconds.')
            sleep(125)
            try:
                r = requests.get(query, headers=self._header)
                return r.json()
            except Exception:
                if r.status_code != 200:
                    raise Exception('Repeated Error after rate limited exceeded and 125 seconds timeout')

        # bad request, unknown status code
        else:
            raise Exception('unknown error code {0} on requesting {1}'.format(r.status_code, query))

    def get_summoner(self, **kwargs) -> pd.DataFrame:
        """Query the riot api for a specific summoner and returns Dataframe.

        One of the following parameters have to be provided:
        :param summoner_id: query summoner by summoner_id.
        :param account_id: query summoner by account_id.
        :param summoner_name: query summoner by summoner_name.
        :param puuid: query summoner by puuid.

        Raises:
            ValueError: thrown if none of [summoner_id, account_id, summoner_name, puuid] gets provided.

        Returns:
            pd.Dataframe: contains information about the summoner by the riot api.
        """

        if 'summoner_id' in kwargs:
            query = endpoints['summoner_v4']['by_id'].format(base_uri=self._base_uri,
                                                             encryptedSummonerId=kwargs['summoner_id'])
        elif 'account_id' in kwargs:
            query = endpoints['summoner_v4']['by_account'].format(base_uri=self._base_uri,
                                                                  encryptedAccountId=kwargs['account_id'])
        elif 'summoner_name' in kwargs:
            query = endpoints['summoner_v4']['by_name'].format(base_uri=self._base_uri,
                                                               summonerName=kwargs['summoner_name'])
        elif 'puuid' in kwargs:
            query = endpoints['summoner_v4']['by_puuid'].format(base_uri=self._base_uri,
                                                                encryptedPUUID=kwargs['puuid'])
        else:
            raise ValueError('[summoner_id, account_id, summoner_name, puuid] is needed to get summoner data')

        result = self.__post_query(query)
        df_result = pd.json_normalize(result)
        df_result.columns = map(self.__snake_case, df_result.columns)
        df_result.rename({'id': 'summoner_id', 'name': 'summoner_name'}, axis=1, inplace=True)
        df_result.set_index('account_id', inplace=True)
        df_result['revision_date'] = pd.to_datetime(df_result['revision_date'], unit='ms')
        return df_result

    def get_match_history(self, **kwargs) -> pd.DataFrame:
        """Query the riot api for match history of summonner

        One of the following parameters have to be provided:
        :param summoner_id: query summoner by summoner_id.
        :param account_id: query summoner by account_id.
        :param summoner_name: query summoner by summoner_name.
        :param puuid: query summoner by puuid.

        optional kwargs:
        champion: champion id
        queue: queue id
        season: season id
        endTime: time in ms
        beginTime: time in ms
        endIndex: amount of games which get returned
        beginIndex: start index of games returned

        Raises:
            ValueError: thrown if none of [summoner_id, account_id, summoner_name, puuid] gets provided.

        Returns:
            pd.Dataframe: match history of summoner
        """
        optional = ['champion', 'queue', 'season', 'endTime', 'beginTime', 'endIndex', 'beginIndex']
        if 'account_id' in kwargs:
            query = endpoints['match_v4']['list'].format(base_uri=self._base_uri,
                                                         encryptedAccountId=kwargs['account_id'])

            query_filter = ['{0}={1}'.format(k, v) for k, v in kwargs.items() if k in optional and v is not None]
            query = '{query}?{optional}'.format(query=query, optional='&'.join(query_filter))
            result = self.__post_query(query)['matches']

            df_matches = pd.json_normalize(result)
            df_matches.columns = map(self.__snake_case, df_matches.columns)
            return df_matches
        elif any(i in kwargs for i in ['summoner_name', 'summoner_id', 'puuid']):
            summoner = self.get_summoner(**kwargs).reset_index().iloc[0, :]
            return self.get_match_history(**{**summoner.to_dict(), **kwargs})
        else:
            raise ValueError(
                '[summoner_id, account_id, summoner_name, puuid] is needed to get match history of summoner')

    def get_match_details(self, match_id: Union[str, int]) -> Dict[str, pd.DataFrame]:
        query = endpoints['match_v4']['details'].format(base_uri=self._base_uri,
                                                        matchId=match_id)

        result = self.__post_query(query)
        frames = {}
        frames.update(self.__extract_match_data(result))
        frames.update(self.__extract_teams_data(result))
        frames.update(self.__extract_bans_data(result))
        frames.update(self.__extract_participants_data(result))
        frames.update(self.__extract_stats_data(result))
        return frames

    def get_timeline(self, match_id: Union[str, int]) -> Dict[str, pd.DataFrame]:
        query = endpoints['match_v4']['timeline'].format(base_uri=self._base_uri,
                                                         matchId=match_id)

        result = self.__post_query(query)

        df_participants = pd.DataFrame()
        df_events = pd.DataFrame()
        for frame in result['frames']:
            for participant in frame['participantFrames'].values():
                buffer = pd.json_normalize(participant, sep='_')
                buffer['timestamp'] = frame['timestamp']
                df_participants = df_participants.append(buffer, ignore_index=True)
            for event in frame['events']:
                buffer = pd.json_normalize(event, sep='_')
                df_events = df_events.append(buffer, ignore_index=True)

        df_participants.columns = map(self.__snake_case, df_participants.columns)
        df_participants['game_id'] = str(match_id)
        df_participants = df_participants.set_index(['game_id', 'timestamp', 'participant_id'])

        df_events.columns = map(self.__snake_case, df_events.columns)
        df_events.participant_id = df_events.participant_id.fillna('0')
        df_events['game_id'] = str(match_id)
        df_events['sequence'] = df_events.groupby(['game_id', 'timestamp', 'participant_id', 'type']).cumcount()
        df_events = df_events.set_index(['game_id', 'timestamp', 'participant_id', 'type'])

        frames = {}
        frames.update({'timeline_participants': df_participants})
        frames.update({'timeline_events': df_events})

        return frames

    def get_challenger_leaderboard(self, queue_type: QueueType) -> Dict[str, pd.DataFrame]:
        query = endpoints['league_v4']['challenger'].format(base_uri=self._base_uri,
                                                            queue_type=queue_type.value)
        result = self.__post_query(query)
        return self.__extract_leaderboard(result)

    def get_grandmaster_leaderboard(self, queue_type: QueueType) -> Dict[str, pd.DataFrame]:
        query = endpoints['league_v4']['grandmaster'].format(base_uri=self._base_uri,
                                                             queue_type=queue_type.value)
        result = self.__post_query(query)
        return self.__extract_leaderboard(result)

    def get_master_leaderboard(self, queue_type: QueueType) -> Dict[str, pd.DataFrame]:
        query = endpoints['league_v4']['master'].format(base_uri=self._base_uri,
                                                        queue_type=queue_type.value)
        result = self.__post_query(query)
        return self.__extract_leaderboard(result)

    def get_league(self, league_id: str) -> Dict[str, pd.DataFrame]:
        query = endpoints['league_v4']['league'].format(base_uri=self._base_uri,
                                                        leagueId=league_id)
        result = self.__post_query(query)

        league = pd.json_normalize(result).drop(columns='entries')
        league.columns = map(self.__snake_case, league.columns)
        league = league.set_index('league_id')

        entries = pd.json_normalize(result, record_path='entries', meta='leagueId')
        entries = entries.loc[:, ~entries.columns.str.startswith('miniSeries')]
        entries.columns = map(self.__snake_case, entries.columns)
        entries = entries.set_index('league_id')

        return {'league': league, 'entries': entries}

    def get_league_entries_of_summoner(self, **kwargs) -> pd.DataFrame:
        """Query the riot api for the league entries of a summoner.

        One of the following parameters have to be provided:
        :param summoner_id: query summoner by summoner_id.
        :param account_id: query summoner by account_id.
        :param summoner_name: query summoner by summoner_name.
        :param puuid: query summoner by puuid.

        Raises:
            ValueError: thrown if none of [summoner_id, account_id, summoner_name, puuid] gets provided.

        Returns:
            pd.Dataframe: contains information about league entries of the summoner by the riot api.
        """

        if 'summoner_id' in kwargs:
            query = endpoints['league_v4']['entries'].format(base_uri=self._base_uri,
                                                             encryptedSummonerId=kwargs['summoner_id'])
            result = self.__post_query(query)
            df_entries = pd.DataFrame()
            for entry in result:
                buffer = pd.json_normalize(entry, sep='_')
                df_entries = df_entries.append(buffer, ignore_index=True)

            df_entries.columns = map(self.__snake_case, df_entries.columns)
            df_entries = df_entries.set_index(['summoner_id', 'queue_type'])
            return df_entries

        elif any(i in kwargs for i in ['summoner_name', 'account_id', 'puuid']):
            summoner = self.get_summoner(**kwargs).reset_index().iloc[0, :]
            return self.get_league_entries_of_summoner(**{**summoner.to_dict(), **kwargs})
        else:
            raise ValueError(
                '[summoner_id, account_id, summoner_name, puuid] is needed to get league entries of summoner')

    def __extract_match_data(self, data: json) -> Dict[str, pd.DataFrame]:
        game = pd.json_normalize(data)
        game['gameCreation'] = pd.to_datetime(game['gameCreation'], unit='ms')
        game = game.drop(columns=['teams', 'participants', 'participantIdentities'])
        game.columns = map(self.__snake_case, game.columns)
        game = game.set_index('game_id')
        return {'matches': game}

    def __extract_teams_data(self, data: json) -> Dict[str, pd.DataFrame]:
        teams = pd.json_normalize(data, record_path=['teams'], meta='gameId', sep='_', max_level=0)
        teams = teams.drop(columns=['bans'])
        teams.columns = map(self.__snake_case, teams.columns)
        teams = teams.set_index(['game_id', 'team_id'])
        return {'teams': teams}

    def __extract_bans_data(self, data: json) -> Dict[str, pd.DataFrame]:
        try:
            bans = pd.json_normalize(data, record_path=['teams', 'bans'], meta=['gameId', ['teams', 'teamId']])
            bans = bans.rename(columns={'teams.teamId': 'teamId'})
            bans.columns = map(self.__snake_case, bans.columns)
            bans = bans.set_index(['game_id', 'team_id', 'pick_turn'])
            return {'bans': bans}
        except KeyError:
            return {'bans': pd.DataFrame()}

    def __extract_participants_data(self, data: json) -> Dict[str, pd.DataFrame]:
        participants = pd.json_normalize(data, record_path=['participantIdentities'], meta=['gameId'])
        participants.columns = map(lambda x: re.sub('player.', '', x), participants.columns)
        participants.columns = map(self.__snake_case, participants.columns)
        participants = participants.set_index(['game_id', 'participant_id'])
        return {'participants': participants}

    def __extract_stats_data(self, data: json) -> Dict[str, pd.DataFrame]:
        stats = pd.json_normalize(data, record_path=['participants'], meta=['gameId'])
        stats = stats.rename(columns={'timeline.lane': 'lane', 'timeline.role': 'role'})
        stats = stats.drop(columns=list(stats.filter(regex='timeline')))
        stats = stats.drop(columns=['participantId'])
        stats.columns = map(lambda x: re.sub('stats.', '', x), stats.columns)
        stats.columns = map(self.__snake_case, stats.columns)
        stats = stats.set_index(['game_id', 'team_id', 'participant_id'])
        return {'stats': stats}

    def __extract_leaderboard(self, data: json) -> Dict[str, pd.DataFrame]:
        df_entries = pd.json_normalize(data, record_path='entries', meta=['leagueId'])
        df_entries.columns = map(self.__snake_case, df_entries.columns)
        df_entries.set_index('league_id', 'summoner_id', inplace=True)

        df_entry = pd.DataFrame(data)
        df_entry.columns = map(self.__snake_case, df_entry.columns)
        df_entry = df_entry.drop(columns='entries').drop_duplicates()
        df_entry = df_entry.set_index('league_id')

        return {'league_entry': df_entry, 'league_entries': df_entries}

    def get_queue_types(self) -> pd.DataFrame:
        df_result = pd.read_json(endpoints['ddragon']['queues'])
        df_result.columns = map(self.__snake_case, df_result.columns)
        df_result = df_result.set_index('queue_id')
        return df_result

    def get_champion_data(self) -> pd.DataFrame:
        content = requests.get(endpoints['ddragon']['champion'].format(local=self._version)).json()
        table = pd.DataFrame()
        for value in content['data'].values():
            table = table.append(pd.json_normalize(value, sep='_'), ignore_index=True)
        table.columns = map(self.__snake_case, table)
        table.columns = [column.replace('stats_', '') for column in table.columns]
        table.rename(columns={'key': 'champion_id'}, inplace=True)
        table.drop(columns=['id'], inplace=True)
        table.set_index('champion_id', inplace=True)
        table['tags'] = table.tags.apply(lambda x: ', '.join(x))
        return table

    @staticmethod
    def get_versions() -> pd.DataFrame:
        versions = requests.get(endpoints['ddragon']['version']).json()
        return pd.DataFrame(versions)

    def get_latest_version(self) -> str:
        return self.get_versions().iloc[0, 0]
