from flask import Flask, render_template, jsonify, request
import json
import logging
import geopy.distance

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load brunnen data
with open('static/brunnen.json', 'r') as f:
    brunnen_data = json.load(f)

@app.route('/')
def index():
    logging.debug("Rendering index page.")
    return render_template('index.html')

@app.route('/api/brunnen', methods=['GET'])
def get_brunnen():
    logging.debug("Fetching brunnen data.")
    return jsonify(brunnen_data)

@app.route('/api/distance', methods=['POST'])
def calculate_distance():
    logging.debug("Calculating distance to the closest trinkbrunnen.")
    user_location = request.json.get('location')
    min_distance = float('inf')
    closest_brunnen = None
    user_coords = (user_location['lat'], user_location['lng'])
    
    for feature in brunnen_data['features']:
        brunnen_coords = (feature['geometry']['coordinates'][1], feature['geometry']['coordinates'][0])
        distance = geopy.distance.distance(user_coords, brunnen_coords).meters
        if distance < min_distance:
            min_distance = distance
            closest_brunnen = feature

    logging.debug(f"Closest trinkbrunnen: {closest_brunnen}, Distance: {min_distance} meters.")
    return jsonify({
        'closest_brunnen': closest_brunnen,
        'distance': min_distance
    })

if __name__ == '__main__':
    logging.debug("Starting Flask app.")
    app.run(debug=True)
