import os
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, MetaData, String
from sqlalchemy.types import JSON


class Playlist(object):
    """
    Playlist is representing a collection of music tracks that can be played sequentially.

    """
    def __init__(self, list_id: int, title : str, thumbnail : str, description : str=None):
        """
        Construct a playlist object.
        :param list_id: Unique playlist id.
        :param title: Playlist title.
        :param thumbnail: Thumbnail image url.

        """
        self._list_id = list_id
        self._title = title
        self._thumbnail = thumbnail
        self._description = description
        self._tracks = []
        self._database_url = os.environ['DATABASE_URL']

    def __len__(self):
        if not self._tracks:
            self._fetch_tracks()
        return len(self._tracks)

    def __iter__(self):
        if not len(self._tracks):
            self._fetch_tracks()
        return iter(self._tracks)

    def _update_data(self):
        """
        Internal method.
        Sync playlist data to the database.

        """
        assert self._list_id != None

        engine = create_engine(self._database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlists', metadata, autoload=True)
            playlist_data = { 'title': self._title, 'thumbnail': self._thumbnail, 'description': self._description }
            result = con.execute(table.update().where(table.c.id == self._list_id).values(data=playlist_data))

    def _update_tracks(self):
        """
        Internal method.
        Sync playlist tracks to the database.

        """
        assert self._list_id != None

        engine = create_engine(self._database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlist_tracks', metadata, autoload=True)
            if len(self._tracks):
                result = con.execute(table.update().where(table.c.list_id == self._list_id).values(data={'tracks': self._tracks}))
                if not result.rowcount:
                    # No recorded tracks for this playlist so insert one
                    con.execute(table.insert().values(list_id=self._list_id, data={'tracks': self._tracks}))
            else:
                # Delete all tracks for this playlist
                con.execute(table.delete().where(table.c.list_id == self._list_id))

    def _fetch_tracks(self) -> list:
        """
        Internal method.
        Sync playlist tracks from the database.

        """
        assert self._list_id != None

        engine = create_engine(self._database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlist_tracks', metadata, autoload=True)
            result = con.execute(table.select().where(table.c.list_id == self._list_id))
            if result and result.returns_rows:
                row = result.fetchone()
                if row:
                    self._tracks = row[table.c.data]['tracks']

    @staticmethod
    def validate_track(track : dict) -> bool:
        """
        Validate playlist track object as it has all the attributes a track must have.
        :param track: track to validate.

        """
        if ('id' not in track and 'title' not in track and
                'thumbnail' not in track and 'artist' not in track):
            return False
        return True

    def append(self, track : dict):
        """
        Append track to the playlist.

        """
        assert track != None
        if not Playlist.validate_track(track):
            raise RuntimeError('Invalid track data structure')

        self._tracks.append(track)
        self._update_tracks()

    def extend(self, iterable : list):
        """
        Extend the list by appending all the tracks from the iterable.
        :param iterable: A list with tracks to extend with.

        """
        assert iterable != None
        assert len(iterable) != 0
        valid_tracks = [track for track in iterable if Playlist.validate_track(track)]
        self._tracks.extend(valid_tracks)
        self._update_tracks()

    def clear(self):
        """
        Remove all tracks from the playlist.

        """
        self._tracks.clear()
        self._update_tracks()

    def remove(self, track_id : str):
        """
        Remove a track from the list.
        Will raise an error if track is not present in the list.
        :param track_id: track id.

        """
        if not len(self._tracks):
            self._fetch_tracks()

        track_to_delete = None
        for track in self._tracks:
            if track['id'] == track_id:
                track_to_delete = track
                break
        assert track_to_delete != None
        self._tracks.remove(track_to_delete)
        self._update_tracks()


    @property
    def list_id(self):
        return self._list_id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, title : str):
        """
        Update playlist title.
        :param title:  Playlist title.

        """
        assert title != None
        self._title = title
        self._update_data()

    @property
    def thumbnail(self) -> str:
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, thumbnail : str):
        self._thumbnail = thumbnail
        self._update_data()
    
    @property
    def description(self):
        return self._description



class Library(object):
    """
    Manages all playlists in the database (create, read and delete).
    """

    database_url = os.environ['DATABASE_URL']

    @staticmethod
    def init_db():
        """
        Create all database tables on startup if not present.

        """
        engine = create_engine(Library.database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            # Playlists database table
            playlists = Table(
                'playlists', metadata,
                Column('id', Integer, primary_key=True),
                Column('data', JSON),
            )
            # Playlist tracks database table.
            playlist_tracks = Table(
                'playlist_tracks', metadata,
                Column('list_id', Integer, primary_key=True),
                Column('data', JSON)
            )
            if not engine.has_table('playlists') and not engine.has_table('tracks'):
                metadata.create_all()

    @staticmethod
    def playlist_data_to_object(table, row):
        """
        Map playlist json data to Playlist object.
        :param table: sqlite table object.
        :param row: sqlite row object.

        """
        list_id = row[table.c.id]
        title, thumbnail, description = row[table.c.data]['title'], row[table.c.data]['thumbnail'], row[table.c.data]['description']
        return Playlist(list_id, title, thumbnail, description)

    @classmethod
    def all(cls) -> list:
        """
        Get all playlists in library.

        """
        playlists = []
        engine = create_engine(Library.database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlists', metadata, autoload=True)
            result = con.execute(table.select())
            if result and result.returns_rows:
                for row in result:
                    playlists.append(cls.playlist_data_to_object(table, row))
        return playlists

    @classmethod
    def playlist(cls, list_id : int) -> Playlist:
        """
        Get a playlist identified by a unique id.
        Will return None if there is no matching playlist. 
        :param list_id: Playlist unique list id.

        """
        assert list_id != None
        engine = create_engine(Library.database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlists', metadata, autoload=True)
            result = con.execute(table.select().where(table.c.id==list_id))
            if result.returns_rows:
                row = result.fetchone()
                if row is not None:
                    return cls.playlist_data_to_object(table, row)
            return None

    @staticmethod
    def create(title : str, thumbnail : str, description : str=None) -> Playlist:
        """
        Create a new playlist in the library.
        :param title: Playlist title.
        :param thumbnail: Thumbnail image url.

        """
        assert title != None
        assert thumbnail != None

        engine = create_engine(Library.database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlists', metadata, autoload=True)
            # Check if playlist with this title already exists
            result = con.execute(table.select().where(table.c.data['title'].as_string()==title))
            if not result.fetchone():
                result = con.execute(table.insert(), data={'title': title, 'thumbnail': thumbnail, 'description': description})
                return Playlist(result.inserted_primary_key[0], title, thumbnail, description)
            return None

    @staticmethod
    def delete(list_id : int):
        """
        Delete a playlist from the library.
        :param list_id: Playlist unique id.

        """
        assert list_id != None
        engine = create_engine(Library.database_url)
        with engine.connect() as con:
            metadata = MetaData(engine)
            table = Table('playlists', metadata, autoload=True)
            con.execute(table.delete().where(table.c.id==list_id))

