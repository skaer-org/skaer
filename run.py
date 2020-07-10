import os
import cherrypy
from skaer.app import Skaer


class Launcher(object):
    """ Cherrypy app launcher"""

    @staticmethod
    def run():
        """ Set configuration values and run cherrypy app """

        cherrypy.config.update({
            'server.socket_port': int(os.environ['PORT']),
            'server.thread_pool': os.cpu_count(),
            'tools.sessions.on': True,
            #'environment': 'production', # for release only
            'log.screen': enable_loging,
            #'tools.sessions.timeout': int(config.get('server.session_duration', 60 * 24)),
        })
        # app entry point.
        cherrypy.tree.mount(Skaer(), '/api', config={
            '/' : {
                    'tools.response_headers.on': True,
                    'tools.response_headers.headers': [('Access-Control-Allow-Origin', '*'),]
                  },
        })
        # Serve all static resources (*.js, *.html and image files)
        resourcedir = os.path.join(os.getcwd(), 'dist')
        cherrypy.tree.mount(None, '/', config={
            '/': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.dir': resourcedir,
                    'tools.staticdir.index': 'index.html',
                    'tools.caching.on': True,
                    'tools.caching.delay': 3600,
                    'tools.gzip.mime_types': ['text/html', 'text/plain', 'text/javascript', 'text/css'],
                    'tools.gzip.on': True
                },
        })
        # Run cherrypy engine
        cherrypy.lib.caching.expires(0)  # disable expiry caching
        cherrypy.engine.start()
        cherrypy.engine.block()


Launcher.run()
