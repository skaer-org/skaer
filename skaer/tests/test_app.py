import os
import sys
import json
import unittest
import threading
import time

import cherrypy
import requests

if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = r'postgresql://skaer:pass@localhost/skaerdb'

from skaer.app import Skaer
from skaer.tests.helpers import create_sample_playlist, drop_db_tables, verify_playlist_in_db, get_playlist_tracks_from_db, add_playlist_tracks_to_db
from skaer.metadata import MetadataProvider as metadata


class CherrypyApp(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        cherrypy.config.update({'environment': 'test_suite'}) # use 'staging' when debuging
        #cherrypy.config.update({'environment': 'staging'})
        cherrypy.quickstart(Skaer(), '/api')

    def shutdown(self):  
        cherrypy.engine.exit()


class TestApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = CherrypyApp()
        cls.app.start()
        # Wait for the server to start
        time.sleep(2)
        cls.db_url = os.environ['DATABASE_URL']
        cls.session_id = '1'

    def test_app_playlist_list(self):
        """
        Test fetching available playlists.

        """
        api_url = r'http://127.0.0.1:8080/api/get_playlist'
        title = 'playlist_list_all'
        thumbnail = 'thumb.example'
        description = 'desc'
        list_id = create_sample_playlist(title, thumbnail, description, TestApp.db_url)
        # Get all playlists and evaluate the result
        r = requests.get(api_url, params={'session_id': TestApp.session_id})
        r.raise_for_status()
        self.assertTrue(r.headers.get('content-type', '').startswith('application/json'))
        json_obj = json.loads(r.json())
        all_playlists = json_obj['playlists']
        self.assertTrue(len(all_playlists) > 0)
        for playlist in all_playlists:
            self.assertTrue(playlist['title'])
            self.assertTrue(playlist['thumbnail'])
        # Check for a single playlist
        r = requests.get(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id})
        r.raise_for_status()
        self.assertTrue(r.headers.get('content-type', '').startswith('application/json'))
        playlist_json = json.loads(r.json())
        self.assertEqual(playlist_json['id'], list_id)
        self.assertEqual(playlist_json['title'], title)
        self.assertEqual(playlist_json['thumbnail'], thumbnail)

    def test_app_playlist_create(self):
        """
        Test the process of creating a playlist.

        """
        api_url = r'http://127.0.0.1:8080/api/create_playlist'
        title = 'Testing app create'
        thumbnail = 'some thumbnail'
        description = 'desc'
        r = requests.post(api_url, params={'session_id': TestApp.session_id}, data=json.dumps({'title': title, 'thumbnail': thumbnail, 'description': description}))
        r.raise_for_status()
        self.assertTrue(r.headers.get('content-type', '').startswith('application/json'))
        json_obj = json.loads(r.json())
        self.assertTrue(json_obj['id'])
        self.assertEqual(json_obj['title'], title)
        self.assertEqual(json_obj['thumbnail'], thumbnail)
        self.assertEqual(json_obj['description'], description)
        # Verify list is in db
        self.assertTrue(verify_playlist_in_db(title, TestApp.db_url))
        # Test create samme playlist again, must return 409
        r = requests.post(api_url, params={'session_id': TestApp.session_id}, data=json.dumps({'title': title, 'thumbnail': thumbnail + TestApp.session_id}))
        self.assertEqual(r.status_code, 409)

    def test_app_playlist_update(self):
        """
        Test the process of updating playlist information.

        """
        api_url = r'http://127.0.0.1:8080/api/update_playlist'
        title = 'Testing app update'
        thumbnail = 'some thumbnail update'
        description = 'desc'
        # Create the playlist first
        list_id = create_sample_playlist(title, thumbnail, description, TestApp.db_url)
        title = 'Testing app update new title'
        r = requests.put(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id}, data=json.dumps({'title': title, 'thumbnail': thumbnail}))
        r.raise_for_status()
        json_obj = json.loads(r.json())
        self.assertEqual(json_obj['id'], list_id)
        self.assertEqual(json_obj['title'], title)

    def test_app_playlist_delete(self):
        """
        Test the process of deleting a playlist.

        """
        api_url = r'http://127.0.0.1:8080/api/delete_playlist'
        title = 'Testing app delete'
        thumbnail = 'some thumbnail delete'
        description = 'desc'
        # Create the playlist first
        list_id = create_sample_playlist(title, thumbnail, description, TestApp.db_url)
        r = requests.delete(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id})
        r.raise_for_status()
        self.assertFalse(verify_playlist_in_db(title, TestApp.db_url))


    def test_app_playlist_tracks_get(self):
        """
        Test fecthing playlist tracks.

        """
        api_url = r'http://127.0.0.1:8080/api/get_tracks'
        # Create sample playlist
        list_id = create_sample_playlist('tracks get', 'thumbnal.test', 'desc', TestApp.db_url)
        test_tracks = [
            {'id' : '1abcd', 'title': 'some title1', 'thumbnail': 'itthumb1a', 'artist': 'artist a'},
            {'id' : '2abce', 'title': 'some title2', 'thumbnail': 'itthumb2b', 'artist': 'artist b'}
        ]
        # Add the tracks to playlist
        add_playlist_tracks_to_db(list_id, test_tracks, TestApp.db_url)
        # Test fetching the tracks via the API
        r = requests.get(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id})
        r.raise_for_status()
        self.assertTrue(r.headers.get('content-type', '').startswith('application/json'))
        json_obj = json.loads(r.json())
        self.assertEqual(json_obj['tracks'], test_tracks)

    def test_app_playlist_tracks_add(self):
        """
        Test add tracks to playlist.

        """
        api_url = r'http://127.0.0.1:8080/api/add_tracks'
        test_tracks = [
            {'id' : '1abcd', 'title': 'some title1', 'thumbnail': 'itthumb1a', 'artist': 'artist a'},
            {'id' : '2abce', 'title': 'some title2', 'thumbnail': 'itthumb2b', 'artist': 'artist b'}
        ]
        # Create sample playlist
        list_id = create_sample_playlist('tracks add', 'thumbnal.test', 'desc', TestApp.db_url)
        r = requests.post(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id}, data=json.dumps({'tracks': test_tracks}))
        r.raise_for_status()
        playlist_tracks = get_playlist_tracks_from_db(list_id, TestApp.db_url)
        self.assertEqual(playlist_tracks, test_tracks)

    def test_app_playlist_tracks_delete(self):
        """
        Test delete track from playlist.

        """
        api_url = r'http://127.0.0.1:8080/api/delete_track'
        list_id = create_sample_playlist('tracks delete', 'thumbnal.test', 'desc', TestApp.db_url)
        test_track = {'id' : '1abcd', 'title': 'some title1', 'thumbnail': 'itthumb1a', 'artist': 'artist a'}
        add_playlist_tracks_to_db(list_id, [test_track], TestApp.db_url)
        # Delete invalid track
        r = requests.post(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id, 'track_id': 'aaaaa'})
        self.assertEqual(r.status_code, 404)
        # Delete the real track
        r = requests.post(api_url, params={'session_id': TestApp.session_id, 'list_id': list_id, 'track_id': test_track['id']})
        r.raise_for_status()
        playlist_tracks = get_playlist_tracks_from_db(list_id, TestApp.db_url)
        self.assertEqual(playlist_tracks, None)

    def test_app_clone(self):
        """
        Test cloning playlist from url.

        """
        api_url = r'http://127.0.0.1:8080/api/clone'
        playlist_url = r'https://www.youtube.com/playlist?list=PLI_TwOrHUsI8MQNW0BvBAwwHYKgyiiiDB'
        playlist_title = r'Top 1000 - Best Hits ever! 90s 80s 00s 90 80 2000'
        data = json.dumps({'url': playlist_url})
        with requests.post(api_url, stream=True, params={'session_id': TestApp.session_id}, data=data) as r:
            r.raise_for_status()
            sys.stdout.write('\n')
            for result in r.iter_content(chunk_size=50, decode_unicode=True):
                json_obj = json.loads(result)
                if json_obj:
                    sys.stdout.write('cloning %s tracks out of %s\r' % (json_obj['progress'], json_obj['total']))
        sys.stdout.write('\n')
        sys.stdout.flush()
        # Verify list is in db
        self.assertTrue(verify_playlist_in_db(playlist_title, TestApp.db_url))
        # Verify playlist is accesible from api'
        r = requests.get(r'http://127.0.0.1:8080/api/get_playlist', params={'session_id': TestApp.session_id})
        r.raise_for_status()
        json_data = json.loads(r.json())['playlists']
        for playlist in json_data:
            if playlist['title'] == playlist_title:
                playlist_tracks = get_playlist_tracks_from_db(int(playlist['id']), TestApp.db_url)
                self.assertTrue(len(playlist_tracks) > 0)
                break

    def test_app_stream(self):
        """
        Test downloading media stream.

        """
        api_url = r'http://127.0.0.1:8080/api/stream'
        with requests.get(api_url, stream=True, params={'session_id': TestApp.session_id, 'track_id': 'eVTXPUF4Oz4'}) as r:
            r.raise_for_status()
            content_length = r.headers.get('Content-Length', None)
            bytes_count = 0
            sys.stdout.write('\n')
            for chunk in r.iter_content(chunk_size=10240):
                bytes_count += len(chunk)
                sys.stdout.write('downloading %s bytes out of %s\r' % (bytes_count, content_length))
        if content_length is not None:
            self.assertEqual(bytes_count, int(content_length))
        sys.stdout.write('\n')
        sys.stdout.flush()

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        drop_db_tables(TestApp.db_url)



        
