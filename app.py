from flask import Flask, render_template, make_response
from flask_cors import CORS  # Import the CORS class
app = Flask(__name__)
CORS(app)  # Initialize CORS with your app instance


@app.route('/')
def index():
    response = make_response(render_template('index.html'))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    app.run(debug=True)
