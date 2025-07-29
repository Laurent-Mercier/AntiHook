# cgi.py
"""
Stub shim for Python 3.13 so that starlette.testclient can import `cgi`.
"""

def parse_header(line):
    # starlette may import this, but tests probably won't actually use it.
    return (), {}

class FieldStorage:
    # stub; will only be constructed in rare multipart cases
    def __init__(self, *args, **kwargs):
        raise RuntimeError("cgi.FieldStorage is not supported in this shim")
