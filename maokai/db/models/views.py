from sqlalchemy import event, DDL

v_summoner_matches = DDL(
    '''
    create view if not exists v_summoner_matches as
    select
        a.game_id,
        a.summoner_name,
        d.name,
        e.description,
        b.season_id,
        b.game_creation,
        b.game_duration,
        c.win,
        c.kills,
        c.deaths,
        c.assists,
        c.role,
        c.lane
    from
        participants a
        join matches b on (a.game_id = b.game_id)
        join stats c on(a.game_id = c.game_id and a.participant_id = c.participant_id)
        join champions d on(c.champion_id = d.champion_id)
        join  queues e on(b.queue_id = e.queue_id)
    order by game_creation desc;
    '''
)

v_summoner_recently_played_champions = DDL(
    '''
    create view if not exists v_summoner_recently_played_champions  as
    select
        summoner_name,
        description,
        name,
        count(*) played
    from
    (
             select
                game_id,
                summoner_name,
                name,
                description,
                game_creation,
                rank() over (partition by summoner_name, description order by game_creation desc) as pos
             from v_summoner_matches
    )
    where
        pos <= 20
    group by summoner_name, description, name;
    '''
)
