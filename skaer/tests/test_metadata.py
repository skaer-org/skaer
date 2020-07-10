import unittest
import sys
from skaer.metadata import MetadataProvider


class MetadataTest(unittest.TestCase):
    """
    Test metadata extraction from various providers.

    """

    def test_metadata_playlist_tracks(self):
        """
        Test playlist tracks metadata match.

        """
        track_count = 0
        list_id = 'PLb98gknbuBNjPSa2zzDP4w8oHZeG6uDBJ'
        playlist = MetadataProvider.playlist(list_id)
        # Check all tracks
        for track_list in MetadataProvider.tracks(list_id):
            track_count += len(track_list)
            for track in track_list:
                self.assertTrue(track['id'])
                self.assertTrue(track['title'])
                self.assertTrue(track['artist'])
                self.assertTrue(track['thumbnail'])
                self.assertTrue(track['duration'])
        # Track count must match playlist total tracks
        self.assertEqual(track_count, playlist['total_tracks'])

    def test_metadata_playlist_fetch(self):
        """
        Test playlist metadata match.

        """
        list_id = 'PLb98gknbuBNjPSa2zzDP4w8oHZeG6uDBJ'
        playlist = MetadataProvider.playlist(list_id)
        # check playlist metadata
        self.assertTrue(playlist['title'])
        self.assertTrue(playlist['description'])
        self.assertTrue(playlist['thumbnail'])
        self.assertTrue(playlist['total_tracks'] > 0)

    def test_metadata_playlist_speedtest(self):
        """
        Test larger playlist for speed.

        """
        # Do a metadata extraction on a large playlist
        tracks_count = 0
        list_id = 'PLI_TwOrHUsI8MQNW0BvBAwwHYKgyiiiDB'
        playlist = MetadataProvider.playlist(list_id)
        self.assertTrue(playlist['total_tracks'] > 0)
        total_tracks = playlist['total_tracks']

        sys.stdout.write('\n')
        for track_list in MetadataProvider.tracks(list_id):
            tracks_count += len(track_list)
            sys.stdout.write('%s tracks out of %s\r' % (tracks_count, total_tracks))

        sys.stdout.write('\n')
        sys.stdout.flush()

    def test_metadata_search(self):
        """
        Test metadata search

        """
        res = MetadataProvider.search('Roxette')
        self.assertTrue(res['items'])
            
