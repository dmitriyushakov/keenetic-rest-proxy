import aiohttp
import hashlib
import logging
import uvicorn
import json
import os

LOGGER = logging.getLogger(__name__)
SCRIPT_PATH = os.path.dirname(__file__)
CONFIG_PATH = f"{SCRIPT_PATH}{os.path.sep}config.json"

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

def asgi_headers_to_request_dict(headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    return {key.decode('utf-8'): value.decode('utf-8') for (key, value) in headers}

async def read_asgi_body(receive) -> bytes:
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return body

class Config:
    router_host: str
    login: str
    password: str
    host: str
    port: int

    def __init__(self, router_host: str, login: str, password: str, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.router_host = router_host
        self.login = login
        self.password = password
        self.host = host
        self.port = port
    
    @staticmethod
    def load_config(config_filename = CONFIG_PATH) -> 'Config':
        with open(config_filename) as config_file:
            config_data = json.load(config_file)
            return Config(**config_data)

class Response:
    status: int
    headers: list[tuple[bytes, bytes]]
    content: bytes

    def __init__(self, status: int, headers: list[tuple[bytes, bytes]], content: bytes) -> None:
        self.status = status
        self.headers = headers
        self.content = content
    
    @staticmethod
    async def from_aiohttp_response(response: aiohttp.ClientResponse) -> 'Response':
        content = await response.read()
        return Response(response.status, response.raw_headers, content)

class KeeneticRestProxyApp:
    config: Config

    def __init__(self):
        self.config = Config.load_config()
        self._session = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        session = self._session
        if session is None:
            LOGGER.info("Session wasn't instantiated yet in this app instance. Create new one.")
            jar = aiohttp.CookieJar(unsafe=True)
            session = aiohttp.ClientSession(cookie_jar = jar)
            self._session = session
            return session
        else:
            return session

    async def __call__(self, scope, receive, send):
        assert scope['type'] == 'http'

        config = self.config
        session = self.session
        headers = asgi_headers_to_request_dict(scope["headers"])
        proxy_response = None

        if scope["method"] == 'GET':
            proxy_request_body = None
        else:
            proxy_request_body = await read_asgi_body(receive)

        for first_try in [True, False]:
            need_authorize = False

            url = f"http://{config.router_host}{scope['path']}"
            async with session.request(method = scope["method"], url = url, headers = headers, data = proxy_request_body) as response:
                status = response.status
                proxy_response = await Response.from_aiohttp_response(response)
                if first_try and status == 401:
                    need_authorize = True
                else:
                    break
            
            if need_authorize:
                LOGGER.info("Router returned 401 code. Trying to pass authorization.")
                auth_url = f"http://{config.router_host}/auth"
                async with session.request(method = 'GET', url = auth_url) as auth_response:
                    auth_response_headers = auth_response.headers
                    if auth_response.status == 200:
                        continue
                    elif auth_response.status != 401:
                        break
                
                md5 = f"{config.login}:{auth_response_headers['X-NDM-Realm']}:{config.password}"
                md5 = hashlib.md5(md5.encode('utf-8'))
                sha = f"{auth_response_headers['X-NDM-Challenge']}{md5.hexdigest()}"
                sha = hashlib.sha256(sha.encode('utf-8'))

                post_data = {"login": config.login, "password": sha.hexdigest()}
                async with session.request(method = 'POST', url = auth_url, json = post_data) as auth_response:
                    if auth_response.status != 200:
                        LOGGER.error(f"Failed to authentificate. Response code - {auth_response.status}")
                        break

        await send({
            'type': 'http.response.start',
            'status': proxy_response.status,
            'headers': proxy_response.headers
        })
        await send({
            'type': 'http.response.body',
            'body': proxy_response.content
        })

if __name__ == '__main__':
    app = KeeneticRestProxyApp()
    uvicorn.run(app, log_config = LOG_CONFIG, port = app.config.port, host = app.config.host)