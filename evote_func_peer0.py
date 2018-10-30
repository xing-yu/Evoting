
# utility
from utility import *
from multiprocessing import *
from socket import *

# GUI
waiting_file = "./html/peer0_wait.html"
tally_file = "./html/peer0_tally.html"
setup_file = "./html/peer0_setup.html"

#----------------------- init metadata --------------------

def init_metadata(server):

    server.metadata = Manager().dict()

    # {ip: (port, status)}
    # {str: (int, str)}
    # peer information
    # status: ONLINE, READY

    server.metadata["peer_info"] = {}

    # int

    server.metadata["num_candidates"] = None

    # {ip: id}
    # {str: int}
    # current peer ide
    # starting from 0
    server.metadata["peer_id"] = {}

    # str
    # ip
    server.metadata["host"] = gethostbyname(getfqdn())

    # int
    # port number
    server.metadata["port"] = 9001

    # bool
    # whether tally
    server.metadata["tally"] = False

#----------------------- handle quest ---------------------

def handle_request(parsed_request, conn, addr, lock, metadata):

    from urllib.parse import urlparse
    from urllib.parse import parse_qs

    # if tally started, no incoming request will be accepted
    if metadata["tally"] == True:
        conn.close()
        return

    # queries
    q = parse_qs(urlparse(parsed_request[1]).query)

    # request source
    host = addr[0]

    # request_type
    if "type" not in q:
        request_type = None
    else:
        request_type = q["type"][0]

    # request value
    if "value" not in q:
        request_value = None
    else:
        request_value = q["value"]

    print("request type: %s"%request_type)
    print("request values: %s"%request_value)

    # local request
    if host == metadata["host"]:

        if metadata['num_candidates'] != None:

            if metadata["tally"] == False:

                # start tally process

                if request_type == "tally":

                    render_page(conn, waiting_file)

                    # received tally signal from user input

                    # TODO: need testing
                    # first broadcast peer information to all nodes
                    broadcast_peer_info(metadata, lock)

                    # TODO: need testing
                    # broadcast number of candidates
                    # broadcast number of active voters
                    broadcast_tally_signal(metadata, lock)

                    print(metadata["tally"])
                    print("tally signal sent!")

                # render tally button page
                else:

                    render_page(conn, tally_file)

            else:

                # tally has started
                # show a waiting page
                render_page(conn, waiting_file)

        else:

            # save number of candidates from user input on peer 0 machine

            if request_type == "num_candidates":

                save_num_candidates(metadata, lock, request_value)

                # after saving number of candidates
                # render tally page
                render_page(conn, fally_file)

            else:

                # show a setup page for number of candidates
                render_page(conn, setup_file)

    # peer requests
    else:

        # node registration

        if request_type == "registration":

            # TODO: need testing
            register_node(metadata, lock, host, conn, request_value)

        elif request_type == "update":

            # TODO: need testing
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

    print("Number of candidates save is %s"%(num_candidates))

#--------------------- register new node ------------------

# save peer registration information and assign node id

# NOTE: id is needed for tallying to create order of votes in the binary vector

def register_node(metadata, lock, host, conn, request_value):

    # register node information

    lock.acquire()

    if host not in metadata["peer_info"]:

        metadata["peer_info"][host] = (int(request_value[0]), "ONLINE")

    lock.release()

    # response success message back to the node

    response = byte("Registration successful!")

    conn.sendall(response)

#------------------------ broadcast peer info -------------

# broadcast peers information to all peers

def broadcast_peer_info(metadata, lock):

    if len(metadata["peer_info"].keys()) == 0:
        print("No active nodes right now!")
        return

    request = "GET /updateinfo?"

    request += "type=updates"

    targets = []

    lock.acquire()

    for peer in metadata["peer_info"].keys():

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

    # set a guard that is the tally is True, 
    # no incomming connection is accepted

    if metadata["tally"] == True:
        return

    # initiate  targets, number of active nodes
    targets = []

    num_active_peers = 0

    lock.acquire()

    # get number of candidates
    num_candidates = metadata["num_candidates"]

    # set tally status to true
    metadata["tally"] = True

    for peer in metadata["peer_info"]:

        if metadata["peer_info"][peer][1] != "READY":
            continue

        targets.append((peer, metadata["peer_info"][peer][0]))

        num_active_peers += 1

    lock.release()

    request = "GET /tallyinfo?"

    request += "type=tally"

    request += "&value=" + str(num_active_peers)

    request += "&value=" + str(num_candidates)

    # send number of active nodes, number of candidates, id,  and tally signal to each active node

    # NOTE: maybe also keep of record of the id

    for idx, each in enumerate(targets):
        temp = request

        temp += "&value=" + str(idx)

        temp += ' HTTP/1.1\r\n'

        s = socket(AF_INET, SOCK_STREAM)

        s.connect(each)

        s.sendall(temp)

        s.close()



























        





    		





