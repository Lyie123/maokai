from maokai import __version__
from maokai.api.league import RiotApi
from requests.exceptions import InvalidHeader
import pandas as pd
import pytest

key = open('api_key').read().rstrip()

def test_version():
    assert __version__ == '0.1.0'

class TestLeagueApi:
    riot = RiotApi(key)

    @pytest.fixture
    def example_summoner(self) -> pd.DataFrame:
        df = pd.read_csv('tests/data/summoner.csv').set_index('account_id')
        return df

    @pytest.fixture
    def example_matchlist(self, request) -> pd.DataFrame:
        df = pd.read_csv('tests/data/matchlist.csv')
        df = df[(df['champion']==154) & (df['season']==13)].reset_index(drop=True)
        return df

    @pytest.fixture
    def example_match_details(self) -> pd.DataFrame:
        bans = pd.read_csv('tests/data/bans.csv').set_index(['game_id', 'team_id', 'pick_turn'])
        matches = pd.read_csv('tests/data/matches.csv').set_index(['game_id'])
        participants = pd.read_csv('tests/data/participants.csv').set_index(['game_id', 'participant_id'])
        stats = pd.read_csv('tests/data/stats.csv').set_index(['game_id', 'team_id', 'participant_id'])
        teams = pd.read_csv('tests/data/teams.csv').set_index(['game_id', 'team_id'])
        df = {
            'bans': bans,
            'matches': matches,
            'participants': participants,
            'stats': stats,
            'teams': teams
        }
        return df

    def test_wrong_api_key(self):
        with pytest.raises(Exception):
            RiotApi('not-valid-key').get_summoner(summoner_name='RonjaRaumpilot')

    @pytest.mark.parametrize('kwargs', [
        {'summoner_name': 'RonjaRaumpilot'},
        {'account_id': 'yuyL70rEQX0f1p5isdmrb4XHKkbLy8J5V-t2WLK1OgHR739fbMuOICfE'},
        {'puuid': 'qU_rNlRS9QW4o8-68R-HM3xADHpgURMjUKkdHVxGZ0Z7k3kLF_wLpiVVXL7iDkMiG01hrRVSjR7HjA'},
        {'summoner_id': 'anpV82GS-2ttqicGTuOIqGePQy8VQ_7bzmQC2QKECB4erQ0d2lBiRxfmmw'}
    ])
    def test_get_summoner(self, kwargs, example_summoner: pd.DataFrame):
        summoner = self.riot.get_summoner(**kwargs)

        # check if player was found
        assert len(summoner) == 1

        # check if columns are correct
        assert all(summoner.columns == example_summoner.columns)

        # check for correct data
        cols = ['summoner_id', 'puuid', 'summoner_name']
        assert pd.DataFrame.equals(summoner[cols], example_summoner[cols])

    def test_get_match_history(self, example_matchlist: pd.DataFrame):
        matches = self.riot.get_match_history(
            summoner_name='RonjaRaumpilot',
            beginTime='1610622113314',
            endTime='1610925255806',
            champion=154,
            season=13
        )

        # check if one match get fetched
        assert len(matches) == len(example_matchlist)

        # check if columns are correct
        assert all(matches.columns == example_matchlist.columns)

        # check for correct data
        assert pd.DataFrame.equals(matches, example_matchlist)

    def test_get_match_details(self, example_match_details: pd.DataFrame):
        details = self.riot.get_match_details(5148931825)

        for name, table in example_match_details.items():
            assert all(details[name].columns == table.columns)
            assert all(details[name] == table)
