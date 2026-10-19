"""Keep OAuth codes and search text out of the server's access-log scope."""
import logging

from starlette.responses import JSONResponse


logger = logging.getLogger(__name__)


class PrivateQueryMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            request_scope = dict(scope)
            scope['query_string'] = b''
            response_started = False

            async def private_response(message):
                nonlocal response_started
                if message['type'] == 'http.response.start':
                    response_started = True
                    message = dict(message)
                    headers = [(k, v) for k, v in message.get('headers', []) if k.lower() != b'cache-control']
                    message['headers'] = headers + [(b'cache-control', b'no-store')]
                await send(message)

            try:
                await self.app(request_scope, receive, private_response)
            except Exception as error:
                # Provider/SQL exception strings can contain mailbox text or
                # credentials. Do not allow the server to log their traceback.
                logger.error('Request failed (%s)', type(error).__name__)
                if response_started:
                    raise RuntimeError('Response interrupted') from None
                response = JSONResponse(status_code=500, content={'detail': 'Request temporarily unavailable'})
                await response(request_scope, receive, private_response)
        else:
            await self.app(scope, receive, send)
