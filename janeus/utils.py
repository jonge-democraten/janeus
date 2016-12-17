import threading


_thread_local = threading.local()


def current_request():
    return getattr(_thread_local, "request", None)


class CurrentRequestMiddleware(object):
    def process_request(self, request):
        _thread_local.request = request
