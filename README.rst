maokai
======

maokai is a wrapper for the riot league of legends api. It is
designed to gather information by the riot by ease and store it in your
relational database.

Installing
----------
Install and update using `pip`:
.. code-block:: text

    $ pip install maokai

.. _pip: https://pip.pypa.io/en/stable/quickstart/

A Simple Example
----------------

How to use the API wrapper:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from maokai.api.riot import RiotApi

    key = 'your-riot-api-key'
    api = RiotApi(key, region='EUW')

    # get summoner from riot api as pd.DataFrame
    summoner = api.get_summoner(summoner_name='ChildShredder69')

    # get match history as pd.DataFrame of summoner Childshredder69 and queue type Ranked Solo 5v5 [420]
    matches = api.get_match_history(summoner_name='ChildShredder69', queue=420)

    # take latest match in match history
    match = matches.game_id[0]

    # get match details as dict of pd.DataFrames
    match_details = api.get_match_details(match)

    # get timeline as dict of pd.DataFrames
    match_timeline = api.get_timeline(match)


How to store data into database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. code-block:: python

    from maokai.db.store import LeagueDb

    key = 'your-riot-api-key'
    con = 'sqlite:///league.sqlite' # Your connection string here.

    db = LeagueDb(key, con)
    db.update_summoner('ChildShredder69', number_of_games=20)