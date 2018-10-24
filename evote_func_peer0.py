
# utility
from utility import *

#----------------------- init metadata --------------------

def init_metadata(server):

    from multiprocessing import *
    from socket import *

    server.metadata = Manager.dict()

    # {ip: (port, status)}
    # {str: (int, str)}
    # peer information
    # status: ONLINE, READY

    server.metadata["peer_info"] = {}

    # int

    server.metadata["num_candidates"] = None

    # int
    # current peer ide
    # starting from 0
    server.metadata["node_id"] = 0

    # str
    # ip
    server.metadata["ip"] = gethostbyname(getfqdn())

    # int
    # port number
    server.metadata["port"] = 9001

    # bool
    # whether tally
    server.metadata["tally"] = False

#----------------------- handle quest ---------------------

def handle_quest(parsed_request, conn, addr, lock, metadata):

    from urllib.parse import urlparse
    from urllib.parse import parse_qs

    # queries
    q = parse_qs(urlparse(parsed_request[1]).query)

    # request source
    host = addr[0]

    # request type
    request_type = q["type"][0]

    # request value
    request_value = q["value"]

    # local request
    if host == '127.0.0.1':

        if metadata['num_candidates'] != None:

            if request_type == "tally":

                # broadcast tally signal

                # first broadcast peer information to all nodes
                broadcast_peer_info(metadata, lock)

                # TODO: implement
                # broadcast number of candidates
                # broadcast number of active voters
                broadcast_tally_signal(metadata, lock)

            else:

                # TODO: implement
                render_page(conn, waiting_file)

        else:

            # save number of candidates

            if request_type == "num_candidates":

                save_num_candidates(metadata, lock, request_value)

    # peer requests
    else:

        # node registration

        if request_type == "registration":

            assign_node_id(metadata, lock, host, conn, request_value)

        elif request_type == "update":

            # update a node from ONLINE to READY
            update_node_info(metadata, lock, request_value)


    # close connection
    conn.close()

#----------------------- save candidate number ------------

# save the number of candidates

def save_num_candidates(metadata, lock, request_value):

    num_candidates = int(request_value[0])

    lock.acquire()

    metadata["num_candidates"] = num_candidates

    lock.release()

#------------------------ assign node id ------------------

# save peer registration information and assign node id

# FIXME: id is no long needed, ip will be unique enough

def assign_node_id(metadata, lock, host, conn, request_value):

    node_id = None

    # register node information

    lock.acquire()

    if host not in metadata["peer_info"]:

        metadata["peer_info"][host] = (int(request_value[0]), "ONLINE")

        node_id = metadata["node_id"]

        metadata["node_id"] += 1

    lock.release()

    # response node id back to the peer

    if node_id != None:

        response = byte(str(node_id))

        conn.sendall(response)

#------------------------ broadcast peer info -------------

# broadcast peers information to all peers

def broadcast_peer_info(metadata, lock):

    from socket import *

    request = "GET /updateinfo?"

    request += "type=updates"

    targets = []

    lock.acquire()

    for peer in metadata["peer_info"]:

        # generate one request for all peers
        request += '&'

        request += "value=" + str(peer)

        request += '&'

        request += "value=" + str(metadata["peer_info"][peer][1])  

        # save peers ip, port
        targets.append((peer, metadata['peer_info'][peer][0]))   

    lock.release()

    request += ' HTTP/1.1\r\n'

    # broadcast to all targets
    request = byte(request)

    for each in targets:

        s = socket(AF_INET, SOCK_STREAM)

        s.connect(each)

        s.sendall(request)

        s.close()

#------------------------ update node info -----------------

# update node information once the node has voted

# status from "ONLINE" to "READY"

# request_value = ['READY']
def update_node_info(metadata, lock, host, request_value):

    lock.acquire()

    if host in metadata["peer_info"]:

        metadata["peer_info"][host] = request_value[0]

    lock.release()

#-------------------- broadcast tally signal ---------------

# once the user click tally on the UI
# peer 0 send out signal to READY nodes to tally

def broadcast_tally_signal(metadata, lock):

    from socket import *

    if metadata["tally"] == True:
        return

    lock.acquire()

    # FIXME: set a guard that is the tally is True, 
    # no incomming connection is accepted

    # set tally status to true
    metadata["tally"] = True

    num_active_peers = 0

    targets = []

    for peer in metadata["peer_info"]:

        if metadata["peer_info"][peer][1] != "READY":
            continue

        targets.append((peer, metadata["peer_info"][peer][0]))

        num_active_peers += 1

    lock.release()

    request = "GET /tallyinfo?"

    request += "type=tally"

    request += "&value=" + str(num_active_peers)

    request += ' HTTP/1.1\r\n'

    for each in targets

        s = socket(AF_INET, SOCK_STREAM)

        s.connect(each)

        s.sendall(request)

        s.close()



























        





    		





