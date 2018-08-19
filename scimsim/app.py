#!/usr/local/bin/python3
from flask import Flask, request


app = Flask(__name__)

@app.before_request
def log_request_info():
    print('\n>>> {} {} {}'.format(request.method, request.path, request.environ.get('SERVER_PROTOCOL')))
    print(*['\n>>> {}: {}'.format(x[0], x[1]) for x in request.headers ])
    print('\n>>> {}'.format(request.get_data()))


@app.after_request
def after(response):
    print('\n<<< {}'.format(response.status))
    print(*['\n<<< {}: {}'.format(x[0], x[1]) for x in response.headers ])
    print('\n<<< {}'.format(response.get_data()))

    return response


@app.route('/', methods=['GET'])
def get_hello():
    return 'hello'


if __name__ == '__main__':
    app.run(debug=True)
