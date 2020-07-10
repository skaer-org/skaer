import os
import unittest
from sqlalchemy import create_engine
from sqlalchemy import Table, MetaData

if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = r'postgresql://skaer:pass@localhost/skaerdb'

from skaer.tests.helpers import verify_playlist_in_db, create_sample_playlist, get_playlist_tracks_from_db, drop_db_tables
from skaer.playlists import Library, Playlist



class PlaylistTest(unittest.TestCase):
    """
    Test the playlist library interface.

    """

    test_tracks = [
        {'id' : '1abcd', 'title': 'some title1', 'thumbnail': 'itthumb1a', 'artist': 'artist a'},
        {'id' : '2abce', 'title': 'some title2', 'thumbnail': 'itthumb2b', 'artist': 'artist b'},
        {'id' : '3abcf', 'title': 'some title3', 'thumbnail': 'itthumb3c', 'artist': 'artist c'},
        {'id' : '4abcg', 'title': 'some title4', 'thumbnail': 'itthumb4d', 'artist': 'artist d'},
        {'id' : '5abch', 'title': 'some title5', 'thumbnail': 'itthumb5e', 'artist': 'artist e'}]

    @classmethod
    def setUpClass(cls):
        Library.init_db()
        cls.db_url = os.environ['DATABASE_URL']

    def test_playlist_create(self):
        """
        Test creating a playlist.

        """
        title = 'playlist title create'
        thumbnail = 'http://localhost/create.png'
        description = 'create description'
        playlist = Library.create(title, thumbnail, description)
        # Test result
        self.assertTrue(playlist.list_id != None)
        self.assertTrue(playlist.title == title)
        self.assertTrue(playlist.thumbnail == thumbnail)
        self.assertTrue(playlist.description == description)
        self.assertTrue(verify_playlist_in_db(title, PlaylistTest.db_url))
        # Try to create the same playlist twice
        playlist = Library.create(title, thumbnail, description)
        self.assertTrue(playlist == None)

    def test_playlist_get(self):
        """
        Test getting a playlist.

        """
        playlist = Library.playlist(2343)
        self.assertTrue(playlist == None)
        # Create a playlist
        title = 'playlist title get'
        thumb = 'http://localhost/get.png'
        description = 'get description'
        list_id = create_sample_playlist(title, thumb, description, PlaylistTest.db_url)
        # Test result
        playlist = Library.playlist(list_id)
        self.assertTrue(playlist.list_id == list_id)
        self.assertTrue(playlist.title == title)
        self.assertTrue(playlist.thumbnail == thumb)
        self.assertTrue(playlist.description == description)
        self.assertTrue(verify_playlist_in_db(title, PlaylistTest.db_url))

    def test_playlist_delete(self):
        """
        Test deleting a playlist.

        """
        # Create a playlist
        list_id = create_sample_playlist('p', 't', 'd', PlaylistTest.db_url)
        # Test
        Library.delete(list_id)
        p = Library.playlist(list_id)
        self.assertTrue(p == None)
        self.assertFalse(verify_playlist_in_db('p', PlaylistTest.db_url))
    
    def test_playlist_all(self):
        """
        Test getting all playlist in the database.

        """
        title1 = 'playlist_all_1'
        title2 = 'playlist_all_2'
        thumbnail = 'thumbnail1234'
        description = 'some description'
        list_id_1 = create_sample_playlist(title1, thumbnail, description, PlaylistTest.db_url)
        list_id_2 = create_sample_playlist(title2, thumbnail, description, PlaylistTest.db_url)
        playlists = Library.all()
        self.assertTrue(len(playlists) == 2)
        self.assertTrue(playlists[0].title == title1)
        self.assertTrue(playlists[1].title == title2)

    def test_playlist_len(self):
        """
        Test playlist len() and check if tracks are synced to database.

        """
        title = 'playlist_with_tracks_append'
        thumbnail = 'thumbnail1234'
        description = 'desc'
        list_id = create_sample_playlist(title, thumbnail, description, PlaylistTest.db_url)

        sample_list = Playlist(list_id, title, thumbnail, description)
        for track in PlaylistTest.test_tracks:
            sample_list.append(track)

        self.assertTrue(len(sample_list) == len(PlaylistTest.test_tracks))
        playlist_tracks = [track for track in sample_list]
        self.assertTrue(len(playlist_tracks) == len(PlaylistTest.test_tracks))
        self.assertTrue(len(playlist_tracks) == len(sample_list))
        # Check results in the database
        db_tracks = get_playlist_tracks_from_db(sample_list.list_id, PlaylistTest.db_url)
        playlist_tracks = [track for track in sample_list]
        self.assertTrue(db_tracks == PlaylistTest.test_tracks == playlist_tracks)

    def test_playlist_extend_and_clear(self):
        """
        Test extending a playlist with new tracks and then clear all the tracks.

        """
        title = 'playlist_with_items_extend'
        thumbnail = 'thumbnail1234'
        description = 'desc extend'
        list_id = create_sample_playlist(title, thumbnail, description, PlaylistTest.db_url)
        sample_list = Playlist(list_id, title, description, thumbnail)
        sample_list.extend(PlaylistTest.test_tracks)
         # Check results in the database
        db_tracks = get_playlist_tracks_from_db(sample_list.list_id, PlaylistTest.db_url)
        playlist_tracks = [track for track in sample_list]
        self.assertTrue(db_tracks == PlaylistTest.test_tracks == playlist_tracks)
        # Test clear method
        sample_list.clear()
        db_tracks = get_playlist_tracks_from_db(sample_list.list_id, PlaylistTest.db_url)
        self.assertTrue(db_tracks == None)
        self.assertTrue(len(sample_list) == 0)

    def test_playlist_remove(self):
        """
        Test removing tracks from playlist.

        """
        title = 'playlist_with_items_remove'
        thumbnail = 'thumbnail1234'
        description = 'desc remove'
        list_id = create_sample_playlist(title, thumbnail, description, PlaylistTest.db_url)
        sample_list = Playlist(list_id, title, thumbnail, description)
        sample_list.extend(PlaylistTest.test_tracks)
        sample_list.remove(PlaylistTest.test_tracks[0]['id'])
        playlist_tracks = [track for track in sample_list]
        self.assertTrue(len(playlist_tracks) == (len(PlaylistTest.test_tracks) - 1))
        self.assertTrue(playlist_tracks[0] == PlaylistTest.test_tracks[1])

    def test_playlist_iterate(self):
        """
        Test iterating a playlist like a python list.

        """
        title = 'playlist_with_items_iterate'
        thumbnail = 'thumbnail1234'
        description = 'desc iterate'
        list_id = create_sample_playlist(title, thumbnail, description, PlaylistTest.db_url)
        sample_list = Playlist(list_id, title, thumbnail, description)
        # Test item iteration
        sample_list.extend(PlaylistTest.test_tracks)
        for idx, track in enumerate(sample_list):
            self.assertTrue(track == PlaylistTest.test_tracks[idx])

    def test_playlist_data(self):
        """
        Test playlist data content for consistency.

        """
        title = 'playlist_test_data'
        thumbnail = 'thumbnail1234'
        description = 'desc data'
        list_id = create_sample_playlist('temp_title', 'temp_thumbnail', 'temp_descr', PlaylistTest.db_url)
        sample_list = Playlist(list_id, 'temp_title', 'temp_thumbnail', 'temp_descr')
        sample_list.title = title
        sample_list.thumbnail = thumbnail
        self.assertTrue(sample_list.title == title)
        self.assertTrue(sample_list.thumbnail == thumbnail)
        self.assertTrue(verify_playlist_in_db(sample_list.title, PlaylistTest.db_url))

    @unittest.skip
    def test_playlist_speed_test(self):
        """
        Do a speed (performance) test.

        """
        title = 'playlist_speed_test'
        thumbnail = 'thumbnail1234'
        list_id = create_sample_playlist(title, thumbnail, 'desc', PlaylistTest.db_url)
        p1 = Playlist(list_id, title, thumbnail)
        track = { 'id': 'QjXcf3wYfhc',
                  'title': 'Jess Glynne No One (Jonas Blue Remix', 
                  'thumbnail': 'https://lh3.googleusercontent.com/ET1uVviDNeKkr7LMkRcHLElE75EsW4dT6quWHlGKQgz36PkFmCQirCPQKu8rewziGgD6cZJvOtuc0yct=w544-h544-l90-rj',
                  'artist': 'Jess Glynne'}
        for _ in range(0,1000):
            p1.append(track)
        p2 = Playlist(list_id, title, thumbnail, 'desc')
        self.assertTrue(len(p2) == 1000)

    @classmethod
    def tearDownClass(cls):
        # Clear all tables from the database
        drop_db_tables(PlaylistTest.db_url)
