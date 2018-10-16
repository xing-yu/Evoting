# this program create a server instance on peer 0
# reponsible for
# keep track of nodes
# update status of nodes
# distribute important infomation
#	number of active nodes
#	number of candidates
#	wether tally result is valid

class Peer0:

	def __init__(self, num_candidates = 2, ip = None, port = 9999, buff_size = 1024, queue_size = None):

		from socket import *
		from multiprocessing import Manager, Lock

		# get peer 0 ip address

		if ip == None:
			hostname = gethostname()

			ip = gethostbyname(hostname)

		self.meta_data = Manager.dict()	# meta data for peer 0
		self.lock = Lock() 				# lock for multiprocessing

		self.meta_data["node_info"] = {}					# {ip: (port, status)}
		self.meta_data["num_active_nodes"] = None 			# int
		self.meta_data["num_candidates"] = num_candidates 	# int
		self.meta_data["tallyisvalid"] = False				# int
		self.meta_data["node_isshared"] = {}				# {ip: bool}
		self.meta_data["node_ispublished"] = {}				# {ip: bool}
		self.meta_data["node_id"] = {}						# {ip: int}
		self.meta_data["cur_id"] = 0						# int
		self.meta_data["host"] = ip
		self.host = ip
		self.port = port
		self.queue_size = queue_size
		self.buff_size = buff_size

	#--------------------- start server --------------------

	def start(self):

		from socket import *

		s = socket(AF_INET, SOCK_STREAM)

		s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

		s.bind((self.host, self.port))

		self.server_socket = s

        self.server_socket.listen(queue_size)

        print("Peer 0 is ready at " + str(self.host) + ": " str(self.port))

        # loop forever to get request
        self.get_requests()

    #--------------------- loop forever to accpt requests ----
    def get_requests(self):

        import multiprocessing

        from evote_func_peer0 import *

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

    #-------------------------- parse requests --------------------
    def parse_request(self, request):
        # extract request line from the http request
        # return a list with [method, path, request_version]

        request_line = request.decode().split('\r\n')[0]

        return request_line.split()

#------------------------------- run ---------------------------------
if name == '__main__':

    peer0 = Node()

    # peer 0 start
    peer0.start()




