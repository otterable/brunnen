from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS
import random
from threading import Thread, Lock
import time
import logging

logging.basicConfig(level=logging.DEBUG)  # Set the log level

app = Flask(__name__)
CORS(app, resources={r"/socket.io/*": {"origins": ["https://otterguessr.ermine.at", "http://localhost:5000"]}})
app.config['SECRET_KEY'] = 'multiplayerisreal'
socketio = SocketIO(app, cors_allowed_origins=["https://otterguessr.ermine.at", "http://localhost:5000"], logger=True, engineio_logger=True)

rooms = {}  # Stores room details
user_rooms = {}  # Maps users to their rooms
user_nicknames = {}  # Maps users to their nicknames
rooms_lock = Lock()  # Lock for thread-safe operations on rooms

def generate_random_nickname():
    animals = ["Otter", "Weasel", "Raccoon", "Fox", "Wolf", "Pigeon", "Goat"]
    return random.choice(animals) + str(random.randint(1000, 9999))

@app.route('/')
def index():
    app.logger.info('Processing default route')
    return render_template('index.html')


def generate_random_coordinates():
    # Placeholder implementation - replace with your actual logic
    lat = random.uniform(-90, 90)
    lng = random.uniform(-180, 180)
    return lat, lng
    
    
@socketio.on('connect')
def on_connect():
    user_id = request.sid
    nickname = generate_random_nickname()
    user_nicknames[user_id] = nickname
    print(f"Debug: User {user_id} connected with nickname {nickname}")
    emit('assigned_nickname', {'nickname': nickname})

@socketio.on('create')
def on_create(data):
    with rooms_lock:
        user_id = request.sid
        nickname = user_nicknames.get(user_id, "Unknown")
        room_id = data['room']
        print(f"Debug: {nickname} attempting to create server {room_id}")

        if room_id in rooms:
            emit('room_creation_failed', {'message': f'Room {room_id} already exists.'})
            return

        rooms[room_id] = {
            'users': {user_id: {'nickname': nickname, 'admin': True}},
            'created_at': time.time(),
            'game_settings': data.get('game_settings', {}),
            'game_started': False
        }
        user_rooms[user_id] = room_id
        join_room(room_id)
        emit('room_created', {
            'message': f'Room {room_id} created successfully.',
            'room': room_id
        }, room=room_id)
        print(f"Debug: {nickname} has successfully created server {room_id}")

game_round_data = {}  # Add this global variable to track round data



@socketio.on('create_multiplayer_game')
def on_create_multiplayer_game(data):
    user_id = request.sid
    if user_id not in user_rooms:
        print(f"Debug: User {user_id} not in any room")
        return

    room_id = user_rooms[user_id]
    print(f"Debug: User {user_id} creating multiplayer game in room {room_id}")

    if room_id in rooms:
        rooms[room_id]['game_settings'] = data
        game_round_data[room_id] = {'current_round': 0, 'round_details': []}
        emit('multiplayer_game_created', data, room=room_id)
        print(f"Debug: Multiplayer game created in room {room_id}")

@socketio.on('start_round')
def on_start_round(data):
    print(f"Debug: start_round event data: {data}")  # This will help you understand what data is being passed
    user_id = request.sid
    room_id = user_rooms.get(user_id)

    if not room_id:
        print(f"Debug: User {user_id} not in any room, can't start round")
        return

    print(f"Debug: Requesting coordinates for new round in room {room_id}")
    emit('request_coordinates', room=room_id)

    if room_id in game_round_data:
        current_round = game_round_data[room_id]['current_round']
        print(f"Debug: Starting round {current_round + 1} in room {room_id}")

        # Generate random coordinates for the StreetView location
        lat, lng = generate_random_coordinates()  # Ensure this function exists or implement it

        lat, lng = generate_random_coordinates()
        emit('new_round', {'round_number': current_round + 1, 'lat': lat, 'lng': lng}, room=room_id)

        # Increment the round number for the next call
        game_round_data[room_id]['current_round'] += 1



@socketio.on('provide_coordinates')
def on_provide_coordinates(data):
    print(f"Debug: Received provide_coordinates event with data: {data}")
    if not data or 'lat' not in data or 'lng' not in data:
        print(f"Debug: Invalid data received for coordinates: {data}")
        return  # Early return if data is invalid

    lat, lng = data['lat'], data['lng']
    user_id = request.sid
    room_id = user_rooms.get(user_id)

    if not room_id:
        print(f"Debug: User {user_id} not in any room, can't proceed with round")
        return

    # Emit the new round data to all clients in the room
    emit('new_round', {'round_number': current_round + 1, 'lat': lat, 'lng': lng}, room=room_id)
    print(f"Debug: Emitting new_round event to room {room_id} with lat: {lat}, lng: {lng}")

    # Increment the round number for the next call
    game_round_data[room_id]['current_round'] += 1

@socketio.on('sync_streetview_data')
def on_sync_streetview_data(data):
    # Emit StreetView data to all players in the same room
    print("Syncing StreetView data:", data)
    emit('streetview_data', data, room=data['room'])
    
    
@socketio.on('join')
def on_join(data):
    with rooms_lock:
        user_id = request.sid
        nickname = user_nicknames.get(user_id, "Unknown")
        room_id = data['room']
        print(f"{nickname} joining room {room_id}")

        if room_id not in rooms or len(rooms[room_id]['users']) >= 10:
            emit('join_error', {'message': f'Cannot join room {room_id}.'})
            return

        rooms[room_id]['users'][user_id] = {'nickname': nickname, 'admin': False}
        user_rooms[user_id] = room_id
        join_room(room_id)
        emit('join_room_announcement', {'message': f'{nickname} joined room {room_id}'}, room=room_id)
        print(f"{nickname} joined room {room_id}")

@socketio.on('start_game')
def on_start_game(data):
    room_id = data['room']
    if room_id in rooms and rooms[room_id]['users'][request.sid]['admin']:
        rooms[room_id]['game_started'] = True
        emit('game_started', rooms[room_id]['game_settings'], room=room_id)
        print(f"Debug: Game started in room {room_id} with settings {rooms[room_id]['game_settings']}")



def get_available_rooms():
    with rooms_lock:  # Ensure thread-safe access to the rooms dictionary
        available_rooms = {}
        for room_id, room_info in rooms.items():
            available_rooms[room_id] = {
                'player_count': len(room_info['users']),
                'created_at': room_info['created_at']
            }
        return available_rooms

    
@socketio.on('list_rooms')
def handle_list_rooms():
    available_rooms = get_available_rooms()
    emit('available_rooms', available_rooms)



@socketio.on('disconnect')
def on_disconnect():
    with rooms_lock:
        user_id = request.sid
        room_id = user_rooms.get(user_id)
        nickname = user_nicknames.get(user_id, "Unknown")

        if room_id and room_id in rooms:
            del rooms[room_id]['users'][user_id]
            if not rooms[room_id]['users']:
                del rooms[room_id]
                print(f"Deleted room {room_id} as it's empty.")

            leave_room(room_id)
            emit('leave_room_announcement', {'message': f'{nickname} left room {room_id}'}, room=room_id)
            print(f"{nickname} left room {room_id}")



def remove_expired_rooms():
    while True:
        with rooms_lock:
            current_time = time.time()
            expired_rooms = [room for room, data in rooms.items() if current_time - data['created_at'] > 3600]
            for room in expired_rooms:
                del rooms[room]
                print(f"Deleted expired room {room}")
        time.sleep(60)  # Check every minute

Thread(target=remove_expired_rooms, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, debug=True)
