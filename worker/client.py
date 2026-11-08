"""Worker HTTP protocol over the private network; no worker bearer token."""
import json
from pathlib import Path
import secrets
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class Rejected(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f'Server returned HTTP {status}')


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def multipart(fields, path):
    boundary = 'neon-' + secrets.token_hex(16)
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="result.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
    chunks.append(Path(path).read_bytes())
    chunks.append(f'\r\n--{boundary}--\r\n'.encode())
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'


class Client:
    def __init__(self, base_url, worker_id, token=None, models=None):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            raise ValueError('SERVER_URL must be an HTTP(S) origin without credentials or a path')
        self.base = base_url.rstrip('/')
        self.prefix = f'/internal/workers/{worker_id}'
        self.models = models

    def request(self, path, data=None, content_type='application/json', timeout=15):
        if data is None:
            data = b'{}'
        elif not isinstance(data, bytes):
            data = json.dumps(data).encode()
        request = Request(self.base + self.prefix + path, data=data,
            headers={'Content-Type':content_type}, method='POST')
        # Each call has its own opener because heartbeats and uploads run in
        # separate threads. Do not follow redirects to another API origin.
        try:
            with build_opener(ProxyHandler({}), NoRedirects()).open(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            raise Rejected(exc.code) from None

    def heartbeat(self, job=None):
        body = {} if job is None else {'job_id':job['id'], 'lease':job['lease']}
        if self.models is not None:
            body['models'] = self.models
        return self.request('/heartbeat', body)

    def claim(self):
        return self.request('/claim', None if self.models is None else {'models':self.models})

    def complete(self, job, path):
        data, kind = multipart({'lease':job['lease'], 'model_id':job['model_id']}, path)
        return self.request(f'/jobs/{job["id"]}/complete', data, kind, timeout=45)

    def fail(self, job, message):
        return self.request(f'/jobs/{job["id"]}/fail', {'lease':job['lease'], 'message':message[:500]})
