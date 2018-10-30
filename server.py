# a new version of server
# work both for peer 0 and nodes
# reduce redundency

import sys
import multiprocessing
from socket import *

class Server:

	# server type can be either node or peer0

	def __init__(self, server_type = 'peer0', peer0_ip = None, peer0_port = 9001, buff_size = 1024, backlog = 1):

		if server_type == "peer0":

			import evote_func_peer0

			self.module = evote_func_peer0

			self.module.init_metadata(self)

		else:

			import evote_func_node

			self.module = evote_func_node

			self.module.init_metadata(self)

			# save peer 0 info
			self.metadata["peer0"] = (peer0_ip, peer0_port)

			# register the node to peer 0

			self.module.register(self.metadata)

		if not self.metadata:

			print("server failed to initialize the metadata.")
			sys.exit(-1)

		self.metadata['type'] = server_type

		self.buff_size = buff_size
		self.backlog = backlog
		self.lock = multiprocessing.Lock()

	#---------------- start the server --------------

	def start(self):

		s = socket(AF_INET, SOCK_STREAM)

		s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

		s.bind((self.metadata['host'], self.metadata['port']))

		if not s:

			print("Fail to create a socket.")

			sys.exit(-1)

		self.server_socket = s

		self.server_socket.listen()

		print("The server is ready at " + str(self.metadata['host']) + ": " + str(self.metadata["port"]))
		print("Sever type is " + self.metadata['type'] + '.')

		self.get_requests()

	#------------- listen to requests ---------------

	def get_requests(self):
		import logging

		self.logger = logging.getLogger("server")

		while True:

			conn, addr = self.server_socket.accept()

			request = conn.recv(self.buff_size)

			parsed_request = self.parse_request(request)

			print("The client is at %s: %s"%(addr[0], addr[1]))
			print(request)

			process = multiprocessing.Process(target = self.module.handle_request, args = (parsed_request, conn, addr, self.lock, self.metadata))

			process.daemon = True

			process.start()

			self.logger.debug("Statted process %r", process)

	#--------------- parse request ------------------

	# all requests are in HTTP format

	def parse_request(self, request):

		request_line = request.decode().split('\r\n')[0]

		return request_line.split()


#-------------------- main ---------------------------

if __name__ == '__main__':

	import logging
	logging.basicConfig(level = logging.DEBUG)

	# starting a node server

	if len(sys.argv) == 2:

		peer0_ip = sys.argv[1]

		server = Server(server_type = 'node', peer0_ip = sys.argv[1])

	# starting a node server with a different peer 0 port

	elif len(sys.argv) == 3:

		peer0_ip = sys.argv[1]

		peer0_port = int(sys.argv[2])

		server = Server(server_type = 'node', peer0_ip = sys.argv[1], peer0_port = int(sys.argv[2]))

	# starting a peer 0 server

	else:

		server = Server()

	try:
		logging.info("Server Started")

		server.start()

	except:

		logging.exception("Unexpected exception")

	finally:

		for process in multiprocessing.active_children():

			process.terminate()
			process.join()

		server.server_socket.close()

		logging.info("Over and Out.")



