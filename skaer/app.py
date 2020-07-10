import os
import json
import requests
import cherrypy
import youtube_dl

from .playlists import Library
from .metadata import MetadataProvider as metadata


class Skaer(object):
    """ Skaer app """

    def __init__(self):
        Library.init_db()

    @classmethod
    def user_allowed(cls, session_id : str) -> bool:
        """
        Validate user session with the server.
        :param session_id: string session id.

        """
        return True

    @cherrypy.expose()
    @cherrypy.tools.allow(methods=['GET'])
    def stream(self, session_id: str, track_id: str):
        """
        Stream audio.
        :param track_id: youtube video id.
        :param session_id: valid session id.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        def audio_stream(vid):
            # Use youtube-dl to extract the audio stream
            with youtube_dl.YoutubeDL({'quiet': True}) as ydl:
                json_out = ydl.extract_info(vid, download=False)
            # Extract the audio stream, best quality
            streams = [f for f in json_out['formats'] if 'audio only' in f['format']]
            best_audio = sorted(streams, key=lambda audio: audio['abr'])[0]
            stream_url = best_audio['url']
            mime_type = 'audio/{}'.format(best_audio['ext'])
            return stream_url, mime_type

        range_header = None
        if 'Range' in cherrypy.request.headers:
               range_header = {'Range' : cherrypy.request.headers['Range']}
        try:
            stream_url, mime_type = audio_stream(track_id)
        except Exception:
            raise cherrypy.HTTPError(404, 'Invalid url')
        # Fetch audio source stream
        resp = requests.get(stream_url, headers=range_header, stream=True)
        if resp.status_code != requests.codes.ok:
             raise cherrypy.HTTPError(404, 'Error fetching stream')
        # stream to client
        #cherrypy.response.headers.update({'Content-Type': mime_type})
        # Forward all source headers
        cherrypy.response.headers.update(resp.headers)
        def content(resp):
            for chunk in resp.iter_content(chunk_size=10240):
                yield chunk
            resp.close()
        return content(resp)
    stream._cp_config = { 'response.stream': True }

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['GET'])
    def get_playlist(self, session_id : str, list_id : int=None):
        """
        Get a playlist with specifid id or return all playlists.
        :param session_id: valid session id.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        result = None
        if list_id is not None:
            playlist = Library.playlist(int(list_id))
            result = json.dumps({'id': playlist.list_id, 'title': playlist.title, 'thumbnail': playlist.thumbnail, 'description': playlist.description})
        else:
            playlists = Library.all()
            json_objects = [{'id': p.list_id, 'title': p.title, 'thumbnail': p.thumbnail, 'description': p.description} for p in playlists]
            result = json.dumps({'playlists' : json_objects})
        return result

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['POST'])
    def create_playlist(self, session_id : str) -> dict:
        """
        Create a playlist with title, thumbnail and description.
        Return the created playlist as json response.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        json_obj = json.loads(cherrypy.request.body.read())
        title, thumbnail, description = json_obj['title'], json_obj['thumbnail'], json_obj.get('description', None)
        playlist = Library.create(title, thumbnail, description)
        if playlist is None:
            raise cherrypy.HTTPError(409, 'Playlist exists')
        else:
            return json.dumps({'id': playlist.list_id, 'title': playlist.title, 'thumbnail': playlist.thumbnail, 'description': playlist.description})

    @cherrypy.expose()
    @cherrypy.tools.allow(methods=['DELETE'])
    def delete_playlist(self, session_id : str, list_id : int):
        """
        Delete a playlist.
        :param session_id: valid session id.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        playlist = Library.playlist(int(list_id))
        if playlist is None:
            raise cherrypy.HTTPError(400, 'No playlist with this id')
        # Delete the tracks first
        playlist.clear()
        Library.delete(playlist.list_id)
        cherrypy.response.status = '204 No Content'

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['PUT'])
    def update_playlist(self, session_id : str, list_id : int) -> dict:
        """
        Update playlist data (title, thumbnail, description) not the tracks.
        :param session_id: valid session id.
        Return the updated playlist as json response.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        playlist = Library.playlist(int(list_id))
        if playlist is None:
            raise cherrypy.HTTPError(400, 'No playlist with this id')

        json_obj = json.loads(cherrypy.request.body.read())
        playlist.title = json_obj['title']
        playlist.thumbnail = json_obj['thumbnail']
        return json.dumps({'id': playlist.list_id, 'title': playlist.title, 'thumbnail': playlist.thumbnail})

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['GET'])
    def get_tracks(self, session_id : str, list_id : int, track_id : str=None):
        """
        Get tracks associated with playlist.
        :param session_id: valid session id.
        :param list_id: playlist id.
        :param track_id: track id, will return only this given track otherwise all playlist tracks are returned.
        
        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        playlist = Library.playlist(int(list_id))
        if playlist is None:
            raise cherrypy.HTTPError(400, 'No playlist with this id')

        tracks_list = [track for track in playlist]
        return json.dumps({ 'tracks': tracks_list })

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['POST'])
    def add_tracks(self, session_id : str, list_id : int):
        """
        Add tracks to playlist.
        :param session_id: valid session id.
        :param list_id: playlist id.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        playlist = Library.playlist(int(list_id))
        if playlist is None:
            raise cherrypy.HTTPError(400, 'No playlist with this id')

        json_obj = json.loads(cherrypy.request.body.read())
        tracks = json_obj['tracks']
        playlist.extend(tracks)
        cherrypy.response.status = '204 No Content'

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['POST'])
    def delete_track(self, session_id : str, list_id : int, track_id : str):
        """
        Delete a track from a playlist.
        :param session_id: valid session id.
        :param list_id: playlist id.
        :param track_id: track to delete.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')
        try:
            playlist = Library.playlist(int(list_id))
            playlist.remove(track_id)
            cherrypy.response.status = '204 No Content'
        except Exception:
            raise cherrypy.HTTPError(404, 'Not found')

    @cherrypy.expose()
    @cherrypy.tools.json_out()
    @cherrypy.tools.allow(methods=['POST'])
    def clone(self, session_id : str):
        """
        Clone a playlist from a url.
        :param session_id: valid session id.
        :param url: playlist url.

        """
        if not self.user_allowed(session_id):
            raise cherrypy.HTTPError(401, 'Unauthorized')

        json_obj = json.loads(cherrypy.request.body.read())
        # https://www.youtube.com/playlist?list=PLI_TwOrHUsI8MQNW0BvBAwwHYKgyiiiDB
        # https://music.youtube.com/playlist?list=PLb98gknbuBNjPSa2zzDP4w8oHZeG6uDBJ
        # Url must be in the following forms
        # https://www.youtube.com/playlist?list=..
        # https://music.youtube.com/playlist?list=..
        url = json_obj['url']

        def progress(list_id, playlist):
            tracks = []
            track_progress = 0
            for track_list in metadata.tracks(list_id):
                track_progress += len(track_list)
                tracks.extend(track_list)
                yield json.dumps({'progress' : str(track_progress), 'total': str(playlist_object['total_tracks'])})
            # add tracks info to the playlist
            playlist.extend(tracks)

        try:
            list_id = url.split('?')[1].split('=')[1]
        except IndexError:
            raise cherrypy.HTTPError(404, 'Invalid url format')
        try:
            playlist_object = metadata.playlist(list_id)
        except Exception:
            raise cherrypy.HTTPError(404, 'Not found')

        playlist = Library.create(playlist_object['title'], playlist_object['thumbnail'], playlist_object['description'])
        return progress(list_id, playlist)
    clone._cp_config = { 'response.stream': True }

