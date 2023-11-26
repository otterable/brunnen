from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS  # Import the CORS class
import time
from threading import Thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multiplayerisreal'  # Replace with a real secret key
CORS(app)  # Initialize CORS with your app instance
socketio = SocketIO(app)

# Global dictionary to track session IDs and their corresponding rooms
user_rooms = {}

# A dictionary to hold room information including creation time
rooms = {}  # Example format: {'room1': {'users': [], 'created_at': timestamp}}


@app.route('/')
def index():
    response = make_response(render_template('index.html'))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@socketio.on('create')
def on_create(data):
    room_id = data['room']
    user_id = request.sid
    nickname = data.get('nickname', 'Player')

    if room_id in rooms:
        emit('room_creation_failed', {'message': f'Room {room_id} already exists.'})
        return

    rooms[room_id] = {'users': {user_id: {'nickname': nickname, 'admin': True}}, 'created_at': time.time()}
    join_room(room_id)
    emit('room_created', {'message': f'Room {room_id} created successfully.', 'room': room_id}, room=room_id)


@socketio.on('leave')
def on_leave(data):
    room_id = data['room']
    user_id = request.sid

    if room_id in rooms and user_id in rooms[room_id]['users']:
        rooms[room_id]['users'].pop(user_id, None)
        leave_room(room_id)
        emit('leave_room_announcement', {'message': f'User {user_id} has left the room {room_id}'}, room=room_id)
    
    if user_id in user_rooms:
        del user_rooms[user_id]


@socketio.on('disconnect')
def on_disconnect():
    user_id = request.sid
    room_id = user_rooms.get(user_id)
    
    if room_id and room_id in rooms:
        # Correctly remove the user from the room's users dictionary
        if user_id in rooms[room_id]['users']:
            del rooms[room_id]['users'][user_id]
            emit('leave_room_announcement', {'message': f'User {user_id} has disconnected from the room {room_id}'}, room=room_id)

            # Delete the room if it's empty
            if len(rooms[room_id]['users']) == 0:
                del rooms[room_id]

    # Remove the user from the user_rooms mapping
    if user_id in user_rooms:
        del user_rooms[user_id]

@socketio.on('send_message')
def handle_send_message_event(data):
    emit('receive_message', data, broadcast=True)


@socketio.on('kick_player')
def on_kick_player(data):
    room_id = data['room']
    user_id = request.sid
    target_id = data['target_id']

    if room_id in rooms and user_id in rooms[room_id]['users']:
        if rooms[room_id]['users'][user_id]['admin']:
            if target_id in rooms[room_id]['users']:
                leave_room(target_id)
                del rooms[room_id]['users'][target_id]
                emit('player_kicked', {'message': f'Player {target_id} has been kicked out.'}, room=room_id)
                
pre_generated_locations = []
                
@socketio.on('pre_generate_locations')
def handle_pre_generate_locations(data):
    global pre_generated_locations
    count = data['count']
    # Logic to pre-generate 'count' number of locations
    pre_generated_locations = generate_locations(count)  # Replace with your location generation logic

@socketio.on('start_multiplayer_game')
def handle_start_multiplayer_game():
    global pre_generated_locations
    # Logic to start the game with pre-generated locations
    emit('start_game', {'locations': pre_generated_locations}, broadcast=True)

@socketio.on('create')
def on_create(data):
    room_id = data['room']
    user_id = request.sid
    nickname = data.get('nickname', 'Player')

    if room_id in rooms:
        emit('room_creation_failed', {'message': f'Room {room_id} already exists.'})
        return

    rooms[room_id] = {'users': {user_id: {'nickname': nickname, 'admin': True}}, 'created_at': time.time()}
    join_room(room_id)
    emit('room_created', {'message': f'Room {room_id} created successfully.', 'room': room_id}, room=room_id)


@socketio.on('list_rooms')
def on_list_rooms():
    current_time = time.time()
    available_rooms = {
        room: {
            'player_count': len(data['users']),
            'players': [{'nickname': user_data['nickname'], 'admin': user_data['admin']} for user_id, user_data in data['users'].items()]
        } for room, data in rooms.items() if current_time - data['created_at'] <= 3600
    }
    emit('available_rooms', available_rooms)


def remove_expired_rooms():
    while True:
        current_time = time.time()
        expired_rooms = [room for room, data in rooms.items() if current_time - data['created_at'] > 3600]
        for room in expired_rooms:
            del rooms[room]
        time.sleep(60)  # Check every minute

# Start the background task for removing expired rooms
Thread(target=remove_expired_rooms, daemon=True).start()




@socketio.on('join')
def on_join(data):
    room_id = data['room']
    user_id = request.sid
    nickname = data.get('nickname', 'Player')

    # Check if the player is already in a room
    if user_id in user_rooms:
        emit('join_error', {'message': 'You are already in a room.'})
        return

    if room_id not in rooms:
        emit('join_error', {'message': 'Room does not exist.'})
        return

    if len(rooms[room_id]['users']) >= 10:  # Max 10 players per room
        emit('room_full', {'message': 'This room is already full.'})
        return

    rooms[room_id]['users'][user_id] = {'nickname': nickname, 'admin': False}
    user_rooms[user_id] = room_id
    join_room(room_id)
    emit('join_room_announcement', {'message': f'{nickname} has joined the room {room_id}'}, room=room_id)

    # Emit updated player list
    emit('update_player_list', {'players': get_player_list(room_id)}, room=room_id)

# Function to get player list with admin status
def get_player_list(room_id):
    return {user_id: {'nickname': data['nickname'], 'admin': data['admin']} for user_id, data in rooms[room_id]['users'].items()}


if __name__ == '__main__':
    socketio.run(app, debug=True)