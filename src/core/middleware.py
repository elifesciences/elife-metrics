import logging
from django.views.decorators.cache import patch_cache_control
from django.utils.cache import patch_vary_headers

LOG = logging.getLogger(__name__)

class DownstreamCaching(object):
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        public_headers = {
            'public': True,
            'max-age': 60 * 5, # 5 minutes, 300 seconds
            'stale-while-revalidate': 60 * 5, # 5 minutes, 300 seconds
            'stale-if-error': (60 * 60) * 24, # 1 day, 86400 seconds
        }
        private_headers = {
            'private': True,
            'max-age': 0, # seconds
            'must-revalidate': True,
        }
        
        #authenticated = request.META[settings.KONG_AUTH_HEADER]
        authenticated = False
        headers = public_headers if not authenticated else private_headers
        
        response = self.get_response(request)
        
        patch_cache_control(response, **headers)
        patch_vary_headers(response, ['Accept'])

        return response
