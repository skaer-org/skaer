from sqlalchemy import create_engine
from sqlalchemy import Table, MetaData


def create_sample_playlist(title : str, thumbnail : str, description : str, db_url : str) -> int:
    engine = create_engine(db_url)
    with engine.connect() as con:
        metadata = MetaData(engine)
        table = Table('playlists', metadata, autoload=True)
        playlist_data={'title': title, 'thumbnail' : thumbnail, 'description': description}
        return con.execute(table.insert(), data=playlist_data).inserted_primary_key[0]


def verify_playlist_in_db(title : str, db_url : str) -> bool:
    engine = create_engine(db_url)
    with engine.connect() as con:
        metadata = MetaData(engine)
        table = Table('playlists', metadata, autoload=True)
        result = con.execute(table.select())
        for row in result:
            if row[table.c.data]['title'] == title:
                return True
        return False


def get_playlist_tracks_from_db(list_id : int, db_url : str) -> list:
    engine = create_engine(db_url)
    with engine.connect() as con:
        metadata = MetaData(engine)
        table = Table('playlist_tracks', metadata, autoload=True)
        result = con.execute(table.select().where(table.c.list_id == list_id))
        row = result.fetchone()
        if row is not None:
            return row[table.c.data]['tracks']
        return None


def add_playlist_tracks_to_db(list_id : int, tracks : list, db_url : str):
    engine = create_engine(db_url)
    with engine.connect() as con:
        metadata = MetaData(engine)
        table = Table('playlist_tracks', metadata, autoload=True)
        return con.execute(table.insert().values(list_id=list_id, data={'tracks': tracks}))


def drop_db_tables(db_url: str):
    engine = create_engine(db_url)
    with engine.connect() as con:
        metadata = MetaData(engine)
        metadata.reflect()
        metadata.drop_all()
