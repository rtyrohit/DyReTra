from datetime import datetime
from flask import request
from flask_socketio import SocketIO, emit, join_room
from config import app

from models.trafficCluster import TrafficCluster
from models.trafficSignalData import TrafficSignalData
from models.socketData import SocketData
from models.clusterActiveData import ClusterActiveData

socketio = SocketIO(app)


@socketio.on('connect', namespace="/tl")
def connectTrafficLight():
    """
        Method to respond on connection of Traffic Light
    """
    data = {
        "cluster_id": int(datetime.timestamp(datetime.now()) / 10)  # TODO: Temporary
    }
    emit('get-cluster-response', {'data': data})
    print(request.sid)
    print("++++Client connected++++")


@socketio.on('disconnect', namespace="/tl")
def disconnectTrafficLight():
    """
        Method to respond on disconnection of Traffic Light
    """
    print(request.sid)
    sid = request.sid
    s = SocketData(sid)
    if s.exists():
        s.update_status(0)
        cluster_id = s.get()['cluster_id']
        c = ClusterActiveData(cluster_id)
        if c.exists():
            c.decrement()
    print("++++Client disconnected++++")


@socketio.on('join-tl-cluster', namespace='/tl')
def joinTrafficCluster(data):
    """
        Join Traffic Light to corresponding cluster
        Args
            data - (dictionary)
                    tl_id - traffic light id
                    cluster_id - cluster id
        Emits
            join-cluster-response - Successful response for joining cluster only to the corresponding to room (cluster)
            simulate-cluster-response - Last running simulation data of the cluster
    """
    sid = request.sid
    tl_id = data['tl_id']
    cluster_id = data['cluster_id']
    s = SocketData(sid)
    if s.exists():
        s.update_status(1)
    else:
        s.create({"cluster_id": cluster_id, "tl_id": tl_id, "sid": sid, "timestamp": datetime.now().timestamp(), "status": 1})
    join_room(cluster_id)
    cluster = TrafficCluster(cluster_id)
    cluster_data = cluster.get()
    del cluster_data['_id']
    c = ClusterActiveData(cluster_id)
    if c.exists():
        c.increment()
    else:
        c.create({"cluster_id": cluster_id, "alive_connection": 1, "simulator_tl_id": tl_id, "timestamp": datetime.now().timestamp()})
    emit('join-cluster-response', {"message": tl_id + " Joined Cluster " + cluster_id, "cluster_data": cluster_data}, room=cluster_id)
    cluster_signal = TrafficSignalData(cluster_id)
    cluster_signal_data = cluster_signal.get()
    emit('simulate-cluster-response',
         {"message": "Signal Received", "data": cluster_signal_data['traffic_signals'], "timestamp": str(cluster_signal_data['timestamp'])},
         room=cluster_id,
         namespace='/tl')


def emit_state(cluster_id, tl_signal, total_time, timestamp):
    """
        Emits simuation data
    """
    socketio.emit('simulate-cluster-response', {"message": "Signal Received", "data": tl_signal, "timestamp": timestamp}, room=cluster_id, namespace="/tl")


def run():
    """
        Method to run socket
    """
    socketio.run(app, debug=True)
