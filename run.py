from flask import Flask
from flask_restx import Api
from flask_cors import CORS

""" from app.resources.guionista import api as guionista_ns
from app.resources. import api as  """

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

api = Api(app, version='1.0', title='', description='API', doc='/docs')

""" api.add_namespace(universo_ns, path='/universos')
api.add_namespace(lugar_ns, path='/lugares') """

if __name__ == '__main__':
    app.run(debug=True)