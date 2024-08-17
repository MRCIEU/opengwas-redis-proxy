from dotenv import load_dotenv
from flask import Flask, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import redis

import os


# Use singleton for Redis connection pool
# https://stackoverflow.com/questions/49398590/correct-way-of-using-redis-connection-pool-in-python
class Singleton(type):
    """
    A metaclass for singleton purpose. Every singleton class should inherit from this class by 'metaclass=Singleton'.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Redis(metaclass=Singleton):
    def __init__(self):
        self.pool = {db: redis.ConnectionPool(host=os.environ['HOST'], port=os.environ['PORT'], password=os.environ['PASS'], db=db, decode_responses=True) for db in range(16)}

    @property
    def conn(self):
        if not hasattr(self, '_conn'):
            self.get_connection()
        return self._conn

    def get_connection(self):
        self._conn = {db: redis.Redis(connection_pool=self.pool[db]) for db in range(16)}


class RedisProxyPipeline:
    def __init__(self, clients: Redis, db: str):
        self.pipe = clients.conn[int(db)].pipeline()

    def sadd(self, arguments):
        return self.pipe.sadd(arguments['name'], *arguments['values'])

    def zrange(self, arguments):
        return self.pipe.zrange(arguments['name'], arguments['start'], arguments['end'], byscore=arguments.get('byscore', False))

    def execute(self):
        return self.pipe.execute()


load_dotenv()

app = Flask(__name__)

clients = Redis()
users = {
    os.environ['AUTH_USERNAME']: generate_password_hash(os.environ['AUTH_PASSWD'])
}

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.route('/', methods=['POST'])
@auth.login_required
def pipeline():
    req = request.get_json()

    try:
        if int(req['db']) not in range(16):
            return {}, 400

        proxy = RedisProxyPipeline(clients, req['db'])

        for c in req['cmds']:
            if c['cmd'] in ['sadd', 'zrange']:
                getattr(proxy, c['cmd'])(c['args'])

        return proxy.execute()
    except Exception as e:
        return {"message": str(e)}, 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6380)
