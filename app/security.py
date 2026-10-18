"""Authenticate before multipart parsing and bound the complete streamed request."""
from __future__ import annotations

import secrets

from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException


class BodyTooLarge(HTTPException):
    def __init__(self):
        super().__init__(413, 'Request exceeds upload limit')


class RequestProtection:
    def __init__(self, app, config):
        self.app = app
        self.config = config

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'cache-control', b'no-store'),
                    (b'x-content-type-options', b'nosniff'),
                    (b'x-frame-options', b'DENY'),
                    (b'referrer-policy', b'no-referrer'),
                    (b'permissions-policy', b'camera=(), microphone=(), geolocation=()'),
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
                ]
            await send(message)
        path = scope['path']
        headers = dict(scope['headers'])
        protected = path == '/api/v1/analyze' or path.startswith('/api/v1/jobs/')
        if protected:
            expected = self.config.api_key.encode()
            supplied = headers.get(b'x-api-key', b'')
            if not expected or not secrets.compare_digest(supplied, expected):
                return await JSONResponse({'detail': 'Invalid or missing X-API-Key'}, 401)(scope, receive, secure_send)
        limit = self.config.max_video_mb * 1024 * 1024 + 1024 * 1024
        if path == '/api/v1/analyze':
            try:
                length = int(headers.get(b'content-length', b'0'))
                if length < 0:
                    raise ValueError
            except ValueError:
                return await JSONResponse({'detail': 'Invalid Content-Length'}, 400)(scope, receive, secure_send)
            if length > limit:
                return await JSONResponse({'detail': 'Request exceeds upload limit'}, 413)(scope, receive, secure_send)
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            if path == '/api/v1/analyze' and message['type'] == 'http.request':
                consumed += len(message.get('body', b''))
                if consumed > limit:
                    raise BodyTooLarge
            return message

        try:
            await self.app(scope, bounded_receive, secure_send)
        except BodyTooLarge:
            await JSONResponse({'detail': 'Request exceeds upload limit'}, 413)(scope, receive, secure_send)
