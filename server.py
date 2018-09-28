# server for peers

class Server:

    def __init__(self, host="", port, peer_0):
        self.host = host        # server ip
        self.port = port        # server port
        self.buff_size = 1024   # buffer size for receive
        self.queue_size = 50    # size for queue of connections
        # self.server_socket, create when starting the server
        # self.peer_0, the server that sync all peer information, preset when starting the server
        # self.peer_0, (ip, port)

    #--------- start server to listen for requests ---------
    def start(self, app, peer_0):

        from socket import *

        s = socket(AF_INET, SOCK_STREAM)

        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        s.bind((self.host, self.port))

        self.server_socket = s

        self.server_socket.listen(queue_size)

        print("Server is ready at " + str(self.host) + ": " str(self.port))

        # set peer_0
        self.peer_0 = peer_0

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
            process = multiprocessing.Process(target = handle_request, args = (parsed_request, conn, addr, self.peer_0, self.environ))

            process.daemon = True
            
            process.start()


    #------------- parse requests -----------------------------------
    def parse_request(self, request):
        # extract request line from the http request
        # return a list with [method, path, request_version]

        request_line = request.decode().split('\r\n')[0]

        return request_line.split()
