
# Keenetic REST Proxy
### Project description
This application allow to bypass Keenetic authorization and receive plain REST requests like you don't need to authorize. It automatically path through authorization challenge and save session cookie when it receive 401 HTTP code from router and sent your requests with cookie. It can be used with home automation. Just write HTTP requests to proxy server and it will authorize automatically.

### Quick start guide
1. Clone git repository and pass into folder.
    ```
    git clone https://github.com/dmitriyushakov/keenetic-rest-proxy.git
    cd keenetic-rest-proxy
    ```
2. Copy `config.json.example` file to `config.json` and fill there next parameters:
    * `router_host` - IP or name of host + port(if it not 80) which used to access to router.
    * `login` - Login which you use to login into admin page of your router.
    * `password` - Password which you use to login into admin page of your router.
    * `host` - Host to bind server socket. Fill to `"0.0.0.0"` if you want to get connection from other hosts.
    * `port` - Port to bind server socket.
3. Create python environment
    **On Windows:**
    ```
    python -m venv env
    env\Scripts\activate
    pip install -r requirements.txt
    ```
    **On Linux:**
    ```
    python -m venv env
    source env/bin/activate
    pip install -r requirements.txt
    ```
4. Start application
    ```
    python keenetic_rest_proxy.py
    ```