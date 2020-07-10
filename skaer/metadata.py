import requests


class MetadataProvider(object):
    """
    A metadata provider is set of functions responsible for extracting the information about a music resource from external source.
    The information consists of playlist information (title, thumbnail image, tracks).
    Also a detailed information about every track is extracted as well (title, artist, album, duration, thumbnail image).

    """
    # youtube api requests permit max 50 results
    max_results = 50

    @classmethod
    def v3_get_request(cls, path : str, headers : dict=None, params : dict=None) -> str:
        """
        Base metadata v3 API request
        :param path: API path.
        :param headers: A dictionary with additional HTTP headers if the api call requires ones.
        :param params: A dictionary with additional HTTP get parameters if the api call requires ones.
    
        """
        req_headers = {
            'Host': 'www.googleapis.com',
            'User-Agent': 'Mozilla/5.0 Firefox/66.0',
            'Accept-Encoding': 'gzip, deflate'
        }
    
        api_endpoint = r'https://www.googleapis.com/youtube/v3/'
    
        req_params = { 'key': 'AIzaSyDU2Rw3_3CtyPSSrKCWFLqcynMp5gqUtsE' }
        if params:
            req_params.update(params)

        url = api_endpoint + path.strip('/')
        if headers:
            req_headers.update(headers)
    
        response = requests.get(url, params=req_params, headers=req_headers)
        if response.status_code != requests.codes.ok:
            response.raise_for_status()
        if response.headers.get('content-type', '').startswith('application/json'):
            return response.json()
        else:
            return response.content.decode('utf-8')

    @classmethod
    def tracks(cls, list_id : str) -> list:
        """
        Returns playlist tracks metadata.
        :param list_id: Playlist unique id.

        """
        def get_tracks_info(ids):
            params = { 'part': 'snippet,contentDetails', 'id': ','.join(ids) }
            result = cls.v3_get_request(path='videos', params=params)
            tracks_info_list = [
                {
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'artist' : item['snippet']['channelTitle'],
                    'thumbnail': item['snippet']['thumbnails']['default']['url'],
                    'duration': item['contentDetails']['duration']
                }
                for item in result['items']
            ]
            return tracks_info_list

        # Fetch track id's
        max_results = cls.max_results
        params = { 'part': 'snippet', 'maxResults': str(max_results), 'playlistId': list_id }
        result = cls.v3_get_request(path='playlistItems', params=params)
        items_ids = [ item['snippet']['resourceId']['videoId'] for item in result['items'] ]

        if result.get('nextPageToken', None) is None:
            return get_tracks_info(items_ids)
        else:
            yield get_tracks_info(items_ids)

        while result.get('nextPageToken', None) is not None:
            next_page_params = params.copy()
            next_page_params['pageToken'] = result['nextPageToken']
            result = cls.v3_get_request(path='playlistItems', params=next_page_params)
            #items_ids.extend([item['snippet']['resourceId']['videoId'] for item in result['items']])
            items_ids = [ item['snippet']['resourceId']['videoId'] for item in result['items'] ]
            yield get_tracks_info(items_ids)

    @classmethod
    def playlist(cls, list_id : str) -> dict:
        """
        Return playlist info.
        :param list_id: Playlist unique id.
    
        """
        result = cls.v3_get_request(path='playlists', params={'part': 'snippet,contentDetails', 'id': list_id, 'maxResults': '1'})
        result = result['items'][0]
        playlist = {
            'title' : result['snippet']['title'],
            'description': result['snippet']['description'],
            'thumbnail' : result['snippet']['thumbnails']['default'],
            'total_tracks' : int(result['contentDetails']['itemCount'])
        }
        return playlist

    @classmethod
    def search(cls, q, search_type=['video', 'channel', 'playlist'],
            channel_id='', order='relevance', safe_search='moderate',
            page_token='', max_results=10, region='US', lang='en'):
        """
        Returns a collection of search results that match the query parameters.
        By default, a search result set identifies matching 
        video, channel, and playlist resources.
        One can also configure queries to only retrieve a specific type of resource.
        :param q: search string.
        :param search_type: acceptable values: 'video' | 'channel' | 'playlist'.
        :param channel_id: limit search to channel id
        :param order: one of: 'date', 'rating', 'relevance',
                            'title', 'videoCount', 'viewCount'
        :param safe_search: one of: 'moderate', 'none', 'strict'
        :param page_token: can be ''
        :return:
    
        """
        # prepare search type
        if not search_type:
            search_type = ''
        if isinstance(search_type, list):
            search_type = ','.join(search_type)
    
        # prepare page token
        if not page_token:
            page_token = ''
    
        # prepare params
        params = {
            'q': q,
            'part': 'snippet',
            'regionCode': region,
            'hl': lang,
            'relevanceLanguage': lang,
            'maxResults': str(max_results)
        }
        if search_type:
            params['type'] = search_type
        if channel_id:
            params['channelId'] = channel_id
        if order:
            params['order'] = order
        if safe_search:
            params['safeSearch'] = safe_search
        if page_token:
            params['pageToken'] = page_token
    
        video_only_params = [
            'eventType', 'videoCaption', 'videoCategoryId', 'videoDefinition',
            'videoDimension', 'videoDuration', 'videoEmbeddable', 'videoLicense',
            'videoSyndicated', 'videoType', 'relatedToVideoId', 'forMine'
        ]
        for key in video_only_params:
            if params.get(key) is not None:
                params['type'] = 'video'
                break
        res = cls.v3_get_request(path='search', params=params)
        return res
