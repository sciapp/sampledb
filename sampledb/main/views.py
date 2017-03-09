import flask

main = flask.Blueprint('main', __name__)


@main.route('/')
def index():
    return flask.render_template('index_old.html')
