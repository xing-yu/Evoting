# server for peers

class Node:

    def __init__(self, peer_0, num_candidates = 2, host = "", port = 9000, buff_size = 1024, queue_size = None):
        
        from multiprocessing import Manager, Lock

        self.meta_data = Manager.dict() # meta data
        self.lock = Lock()              # lock for multiprocess 

        self.peer_0 = peer_0            # (ip, port) of peer 0
        self.host = host                # server ip
        self.port = port                # server port
        self.buff_size = buff_size      # buffer size for receive
        self.queue_size = queue_size    # size for queue of connections

        self.num_candidates = num_candidates    # int, number of candidates for voting

        # self.peer_0, the server that sync all peer information, preset when starting the server
        # self.peer_0, (ip, port)

        # register node
        self.register()

        # initialize metadata
        self.init_meta()

    #---------------- initialize meta data -----------------
    def init_meta(self):

        self.meta_data["peer_info"] = {}    # {ip: (port, status)}
        self.meta_data["peer_votes"] = {}   # {ip: vote(int)}
        self.meta_data["peer_shares"] = {}  # {ip: share(int)}
        self.meta_data["shares"] = []       # [int]
        self.meta_data["local_vote"] = None 
        self.meta_data["masked_vote"] =None
        self.meta_data["Zm"] = None
        self.meta_data["tally_result"] = None
        self.meta_data["vector_len"] = None
        self.meta_data["num_active_peers"] = None

        # TODO: since Zm cannot be defined until tally
        # save absolute vote (which candidate the node voted for)
        # in meta data

    #---------------- node registration --------------------
    def register(self):
        from socket import *
        import sys

        # initialize a socket to send node info to peer 0
        # peer 0 must be working

        s = socket(AF_INET, SOCK_STREAM)

        try:
            
            s.connect(self.peer_0)
        
        except:

            print("Cannot connect to peer 0!")

            sys.exit(-1)

        # create a request to send port information to peer 0

        request = "GET /nodeinfo?"

        request += 'type=registration&'

        request += 'value=' + str(self.port)

        request += 'HTTP/1.1\r\n'

        s.sendall(request.encode())

        node_id = s.recv(1024).decode()

        self.meta_data["node_id"] = int(node_id)

        print("Node registration is successful! The node id is " + node_id)

        s.close()        

    #--------- start server to listen for requests ---------
    def start(self):

        from socket import *

        s = socket(AF_INET, SOCK_STREAM)

        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        s.bind((self.host, self.port))

        self.server_socket = s

        self.server_socket.listen(queue_size)

        print("Server is ready at " + str(self.host) + ": " str(self.port))

        # loop forever to get request
        self.get_requests()

    #---------- loop forever to accept incoming connections -------
    def get_requests(self):

        import multiprocessing

        from evote_func_node import *

        if self.server_socket == None:
            return -1

        while True:

            conn, addr = self.server_socket.accept()

            request = conn.recv(self.buff_size)

            parsed_request = self.parse_request(request)

            # create a process to handle the request
            process = multiprocessing.Process(target = handle_request, args = (parsed_request, conn, addr, self.lock, self.meta_data))

            process.daemon = True
            
            process.start()


    #------------- parse requests -------------------------
    def parse_request(self, request):
        # extract request line from the http request
        # return a list with [method, path, request_version]

        request_line = request.decode().split('\r\n')[0]

        return request_line.split()

#--------------------------- run -----------------------------------
if name == '__main__':

    node = Node(peer_0)

    # node start
    node.start()

