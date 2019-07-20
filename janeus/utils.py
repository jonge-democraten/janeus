import threading


_thread_local = threading.local()


def current_request():
    return getattr(_thread_local, "request", None)


class CurrentRequestMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """ New MIDDLEWARE behavior.
        """
        _thread_local.request = request
        return self.get_response(request)

    def process_request(self, request):
        """ Old MIDDLEWARE_CLASSES behavior.
        """
        _thread_local.request = request
