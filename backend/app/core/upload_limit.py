"""Bound multipart uploads before parsing, including chunked requests."""
import tempfile
from starlette.responses import JSONResponse


class UploadLimitMiddleware:
    def __init__(self, app, limit=101 * 1024 * 1024):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') != 'POST' or not scope.get('path', '').endswith('/analysis'):
            return await self.app(scope, receive, send)
        size = 0
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as body:
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                chunk = message.get('body', b'')
                size += len(chunk)
                if size > self.limit:
                    response = JSONResponse({'error': {'status_code': 413, 'message': 'Upload exceeds maximum request size.'}}, status_code=413)
                    return await response(scope, receive, send)
                body.write(chunk)
                if not message.get('more_body', False):
                    break
            body.seek(0)
            consumed = 0
            async def replay():
                nonlocal consumed
                if consumed >= size:
                    return await receive()
                chunk = body.read(64 * 1024)
                consumed += len(chunk)
                return {'type': 'http.request', 'body': chunk, 'more_body': consumed < size}
            # Empty bodies still need one terminating request message.
            if size == 0:
                async def empty():
                    return {'type': 'http.request', 'body': b'', 'more_body': False}
                return await self.app(scope, empty, send)
            await self.app(scope, replay, send)
