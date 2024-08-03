from flask import Flask, render_template, jsonify, request
import json
import logging
import geopy.distance
import requests

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load brunnen data
with open('static/brunnen.json', 'r') as f:
    brunnen_data = json.load(f)

# Load Google Maps API key from environment variable or config file
with open('config.json', 'r') as f:
    config = json.load(f)
google_maps_api_key = config['google_maps_api_key']

@app.route('/')
def index():
    logging.debug("Rendering index page.")
    return render_template('index.html', google_maps_api_key=google_maps_api_key)

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
    user_coords = {'lat': user_location['lat'], 'lng': user_location['lng']}

    for feature in brunnen_data['features']:
        brunnen_coords = {'lat': feature['geometry']['coordinates'][1], 'lng': feature['geometry']['coordinates'][0]}
        distance = geopy.distance.distance((user_coords['lat'], user_coords['lng']), (brunnen_coords['lat'], brunnen_coords['lng'])).meters
        if distance < min_distance:
            min_distance = distance
            closest_brunnen = feature

    # Calculate walking distance using Google Maps API
    brunnen_coords = {'lat': closest_brunnen['geometry']['coordinates'][1], 'lng': closest_brunnen['geometry']['coordinates'][0]}
    walking_distance = get_walking_distance(user_coords, brunnen_coords)

    logging.debug(f"Closest trinkbrunnen: {closest_brunnen}, Distance: {min_distance} meters, Walking distance: {walking_distance} meters.")
    logging.debug(f"FIRST SELECTED BRUNNEN: {closest_brunnen['properties'].get('name', 'Unknown')} at {brunnen_coords}")
    return jsonify({
        'closest_brunnen': closest_brunnen,
        'distance': min_distance,
        'walking_distance': walking_distance
    })

@app.route('/api/walking-distance', methods=['POST'])
def walking_distance():
    logging.debug("Calculating walking distance.")
    user_location = request.json.get('userLocation')
    brunnen_location = request.json.get('brunnenLocation')
    walking_distance = get_walking_distance(user_location, brunnen_location)
    return jsonify({'walking_distance': walking_distance})

def get_walking_distance(start, end):
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start['lat']},{start['lng']}&destination={end['lat']},{end['lng']}&mode=walking&key={google_maps_api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        directions = response.json()
        if directions['routes']:
            return directions['routes'][0]['legs'][0]['distance']['value']
    return None

if __name__ == '__main__':
    logging.debug("Starting Flask app.")
    app.run(debug=True)