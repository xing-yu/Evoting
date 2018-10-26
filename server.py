# a new version of server
# work both for peer 0 and nodes
# reduce redundency

import sys
from multiprocessing import *
from socket import *

class Server:

	# server type can be either node or peer0

	def __init__(self, server_type = 'node', peer0_ip = None, peer0_port = None, buff_size = 1024, queue_size = None):

		if server_type == "peer0":

			import evote_func_peer0

			self.module = evote_func_peer0

			self.module.init_metadata(self)

		else:

			import evote_func_node

			self.module = evote_func_node

			self.module.init_metadata(self)

			# init metadata
			module.init_metadata(self)

			# save peer 0 info
			self.metadata["peer0"] = (peer0_ip, peer0_port)

			# FIXME: peer 0 should also give number of candidates

			# register and get node id from peer 0
			# NOTE: node id is no longer needed

			module.register(metadata)

		if not self.metadata:

			print("server failed to initialize the metadata.")
			sys.exit(-1)

		self.metadata['type'] = server_type

		self.buff_size = buff_size
		self.queue_size = queue_size
		self.lock = Lock()

	#---------------- start the server --------------

	def start(self):

		s = socket(AF_INET, SOCK_STREAM)

		s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

		s.bind((self.metadata['host'], self.metadata['port']))

		if not s:

			print("Fail to create a socket.")

			sys.exit(-1)

		self.server_socket = s

		self.server_socket.listen(self.queue_size)

		print("The server is ready at " + str(self.metadata['host']) + ": " + str(self.metadata["port"]))
		print("Sever type is " + self.metadata['type'] + '.')

		self.get_requests()

	#------------- listen to requests ---------------

	def get_requests(self):

		while True:

			conn, addr = self.server_socket.accept()

			request = conn.recv(self.buff_size)

			parsed_request = self.parse_request(request)

			process = multiprocessing.Process(target = self.module.handle_request, args = (parsed_request, conn, addr, self.lock, self.metadata))

			process.daemon = True

			process.start()

	#--------------- parse request ------------------

	# all requests are in HTTP format

	def parse_request(self, request):

		request_line = request.decode().split('\r\n')[0]

		return request_line.split()


#-------------------- main ---------------------------

if name == '__main__':

	if len(sys.argv) > 1:

		# FIXME: use try except to make sure peer0 info is provided
		server = Server(server_type = sys.argv[1], peer0_ip = sys.argv[2], peer0_port = int(sys.argv[3]))

	else:

		server = Server()

	try:

		server.start()

	except:

		# TODO:log exceptions

	finally:

		for process in multiprocessing.active_children():

			process.terminate()
			process.join()



