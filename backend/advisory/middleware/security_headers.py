"""Security response headers middleware.

Emits the Content-Security-Policy (and any other headers) defined in
``settings.CSP_HEADERS``. Previously ``CSP_HEADERS`` was built in settings but
never attached to responses, so the policy did nothing. This middleware wires
it up. Headers already present on a response are left untouched.
"""

from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.headers = dict(getattr(settings, "CSP_HEADERS", {}) or {})

    def __call__(self, request):
        response = self.get_response(request)
        for name, value in self.headers.items():
            if value and name not in response:
                response[name] = value
        return response
