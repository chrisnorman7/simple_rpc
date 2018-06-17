"""Run a test server."""

from os.path import getmtime
import os.path
from autobahn.twisted.websocket import WebSocketServerFactory, listenWS
from klein import Klein
from simple_rpc import SimpleRPCContainer

app = Klein()
js_file = os.path.join('simple_rpc', 'simple_rpc.js')
timestamp = getmtime(js_file)
with open(js_file, 'r') as f:
    js_code = f.read()

html = """
<!doctype html>
<html lang="en">
<head>
<title>SimpleRPC Test Server</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta charset="UTF-8">
</head>
<body>
<h1>SimpleRPC</h1>
<p>This is a test server showing SimpleRPC.</p>
<p><label>Text: <input type="text" id="text"></label></p>
<p><input type="button" id="alert" value="Alert Text"></p>
<p><input type="button" id="error" value="Generate an error"></p>
<script src="/js/?$timestamp$"></script>
<script>
const soc = new WebSocket('ws://localhost:9000')
const rpc = new RPC(soc)
const text = document.getElementById("text")
document.getElementById("alert").onclick = () => {
    let val = text.value
    rpc.python.alert(text.value).then(
        (value) => alert(value)
    ).catch(
        (message) => alert(`Error: ${message}`)
    )
    text.value = ""
}

document.getElementById("error").onclick = () => {
    rpc.python.problem().then(
        () => alert("This shouldn't happen.")
    ).catch(
        message => alert(message)
    )
}
</script>
</body>
</html>
""".replace('$timestamp$', str(timestamp))


@app.route('/js/')
def js(request):
    """Return some JavaScript."""
    return js_code


@app.route('/')
def index(request):
    return html


c = SimpleRPCContainer()


@c.register
def alert(text):
    """Handle text."""
    if text:
        return f'I received: {text}'
    raise Exception('You must enter something.')


@c.register
def problem():
    raise Exception('That was an error.')


if __name__ == '__main__':
    f = WebSocketServerFactory('ws://0.0.0.0:9000')
    f.protocol = c.protocol
    listenWS(f)
    app.run(host='0.0.0.0', port=8080)
