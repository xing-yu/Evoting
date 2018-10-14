# server for peers

class Server:

    def __init__(self, peer_0, host = "", port = 9000, buff_size = 1024, queue_size = None):
        
        from multiprocessing import Manager, Lock

        self.environ = Manager.dict()   # environment dict
        self.lock = Lock()              # lock for multiprocess 

        # keep track of whether a peer has shared
        self.environ['peer_has_shared'] = {}

        self.peer_0 = peer_0            # (ip, port) of peer 0
        self.host = host                # server ip
        self.port = port                # server port
        self.buff_size = buff_size      # buffer size for receive
        self.queue_size = queue_size    # size for queue of connections

        # self.peer_0, the server that sync all peer information, preset when starting the server
        # self.peer_0, (ip, port)

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

        request += 'port=' + str(self.port)

        request += 'HTTP/1.1\r\n'

        s.sendall(request.encode())

        # TODO: make peer 0 send back a peer id

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

        # TODO
        # creat another process/thread for heartbeat
        # self.app.heartbeat(self.peer_0)

    #---------- loop forever to accept incoming connections -------
    def get_requests(self):

        import multiprocessing

        if self.server_socket == None:
            return -1

        while True:

            conn, addr = self.server_socket.accept()

            request = conn.recv(self.buff_size)

            # TODO: consider if the request parse should be moved to app
            parsed_request = self.parse_request(request)

            # create a process to handle the request
            process = multiprocessing.Process(target = handle_request, args = (parsed_request, conn, addr, self.lock, self.environ))

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

    node = Server(peer_0)

    # register node with peer_0
    node.register()

    # node start
    node.start()

