import os
from rest_framework import authentication, exceptions

class SimpleUser:
    pk = None
    is_authenticated = True
    is_anonymous = False

class HeaderAPIKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None  # No key provided, let other mechanisms handle it or fail later

        internal_key = os.environ.get('INTERNAL_API_KEY')
        
        if not internal_key:
            raise exceptions.AuthenticationFailed('API Key authentication is enabled but not configured on the server.')

        if api_key != internal_key:
            raise exceptions.AuthenticationFailed('Invalid API Key.')

        return (SimpleUser(), None)
