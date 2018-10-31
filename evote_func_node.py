# The Evote application
# Written in functions for multiprocessing

import sys
from utility import *
from multiprocessing import *
from socket import *

# macros

vote_file = "./html/node_vote_page.html"	# html file for rendering the voting page
waiting_file = "" # html file to show user that vote is successfully received

# vote page should have one form
# action = "submitVote"
# query name = "vote"
# query value = [the vote]
# e.g., /submitVote?vote=1

#------------------- init metadata ----------------------

def init_metadata(server):

	server.metadata = Manager().dict()

	# get ip of the node
	temp = getfqdn()
	server.metadata["ip"] = gethostbyname(temp)

	# host ip address, str
	server.metadata['host'] = ''

	# server port, int
	server.metadata['port'] = 9000

	# peer information, {ip : (port (int), status (str))}
	# status:
	# ONLINE -> registered with peer 0
	# READY -> vote acquired and ready for tally

	server.metadata['peer_info'] = {}

	# peer votes, {ip (str) : vote (int)} 
	server.metadata['peer_votes'] = {}

	# peer shares, {ip : share}
	server.metadata['peer_shares'] = {}

	# vote by local user, int, 0 index, represent which candidate
	server.metadata['local_vote'] = None

	# vector of shares for (n, n) screct sharing, [int]
	server.metadata['shares'] = []

	# int
	# local vote -> binary vector -> int -> masked with peer shares
	server.metadata['masked_vote'] = None

	# int
	# all shares s_i satify that s_i >= 0 and s_i < Zm
	# Zm = 2**vector_len
	server.metadata['Zm'] = None

	# str
	# value of the sumation of all votes from all nodes
	# value -> binary vector
	# a vector of vote count for candidates
	server.metadata['tally_result'] = None

	# int
	# number of active peers at tally
	server.metadata['num_active_peers'] = 0

	# int
	# number of candidates
	server.metadata['num_candidates'] = None

	# num_candidates * num_active_peers
	server.metadata['vector_len'] = None

	# (str, int)
	# peer 0 ip : port
	server.metadata['peer0'] = None

#----------------- identify request ---------------------

def handle_request(parsed_request, conn, addr, lock, metadata):

	from urllib.parse import urlparse
	from urllib.parse import parse_qs

	# queries
	q = parse_qs(urlparse(parsed_request[1]).query)

	# request source
	host = addr[0]

	# request type
	if "type" not in q:
		request_type = None
	else:
		request_type = q['type'][0]

	# request value
	if "type" not in q:
		request_value = None
	else:
		request_value = q['value']

	# local requests

	if host == '127.0.0.1':

		if metadata['local_vote'] != None:

			# return tally result page
			if metadata['tally_result'] != None:

				# the result page shows how many votes each candidate gets
				render_result_page(metadata, lock)

			# return waiting page
			else:

				render_page(conn, waiting_file)

		# save local user vote
		# elif request_type == 'vote' and metadata['local_vote'] == None:
		else:
			
			# save local user vote
			
			if request_type == 'vote':
		
				# save local user's vote
				save_user_vote(metadata, lock, host, request_value)

				# send status update to peer 0
				status_update(metadata, lock)

			# return voting page
			
			else:

				# unique view, need to implement individually
				render_page(conn, vote_file)

	# peer 0 requests
	elif host == metadata['peer0'][0]:

		# start tally
		# FIXME: add a guard
		# if tally signal is already received, the node shall not tally again
		if request_type == 'tally':

			# save node id/ number of active peers from peer 0
			save_tally_info(metadata, lock, request_value)

			# generate shares and publish to all active peers
			convert_vote(metadata, lock)

			# generate shares for all peers
			generate_shares(metadata, lock, request_value)

			# publish shares
			publish_shares(metadata, lock, request_value)

		# update peer information from peer 0
		elif request_type == 'updates':

			# update peer info
			# request value: [ip, status, ip, status, ...]
			update_peer_info(metadata, lock, request_value)

	# peer requests
	else:

		# save share from a peer
		if request_type == 'share':

			# save peer share
			save_peer_share(metadata, lock, host, request_value)

			# if all shares received
			# NOTE: could make the function faster by storing number of peers that already shared
			if all_peers_shared(metadata):

				# mask local vote
				generate_mask_vote(metadata)

				# publish vote
				publish_vote(metadata)

		# save vote from a peer
		elif request_type == 'vote':

			# save peer's vote
			save_peer_vote(metadata, lock, request_value)

			# if all vote received
			# NOTE: same as above
			if all_peers_published(metadata):

				# tally result
				tally_votes(metadata)

				# NOTE: how to send this to local client?
				# show tally result
				# render_result_page(metadata, lock)

	# close connection
	conn.close()

#---------------- register function ---------------------

# this function register node with peer 0

def register(metadata):

	# initialize a socket to send node info to peer 0
	# peer 0 must be working

	s = socket(AF_INET, SOCK_STREAM)

	print("Trying to connect and register to peer 0 at %s:%s" % (metadata['peer0'][0], metadata['peer0'][1]))

	#s.connect(metadata['peer0'])

	try:
			
		s.connect(metadata['peer0'])
		
	except:

		print("Failed to connect to peer 0!")

		sys.exit(-1)

	# create a request to send port information to peer 0

	request = "GET /nodeinfo?"

	request += 'type=registration&'

	request += 'value=' + str(metadata['port'])

	request += ' HTTP/1.1\r\n'

	s.sendall(request.encode())

	response = s.recv(1024).decode()

	print(response)

	s.close()    

#---------------- updates peer info ---------------------
# receive updates of peer status from peer 0
# and store the info in local metadata
# request value: [ip, status, ip, status, ...]

def update_peer_info(metadata, lock, request_value):

	# NOTE: currently, node only keeps status information of all peers
	# 		no port information is kept. 
	# 		if port number is consistent across all peers
	#		then it is not necessary

	host, status = None, None

	lock.acquire()
	
	temp = metadata['peer_info']
	
	local_ip = metadata['ip']

	for idx, value in enumerate(request_value):
		if idx % 2 == 0:
			host = value
		else:
			status = value

			# exclude self related information
			if host != local_ip:

				temp[host] = (metadata['port'], status)
				
	metadta['peer_info'] = temp

	lock.release()
	
#------------------ save user vote -----------------------
# save local user's vote
# the number indicates which candidate the user voted for
def save_user_vote(metadata, lock, request_value):

	lock.acquire()

	metadata["local_vote"] = int(request_value[0])

	lock.release()

#------------------ save peer vote -----------------------
# request_value: [value]
def save_peer_vote(metadata, lock, host, request_value):

	# if the source is not valid, ignore
	if metadata["peer_info"][host][1] != 'READY' or host not in metadata["peer_info"]:
		return

	lock.acquire()
	
	temp = metadata["peer_votes"]

	temp[host] = int(request_value[0])
	
	metadata["peer_votes"] = temp

	lock.release()

#----------------- save peer share -----------------------
# request_value: [value]
def save_peer_share(metadata, lock, host, request_value):

	# if the source is not valid, ignore
	if metadata['peer_info'][host][1] != 'READY' or host not in metadata['peer_info']:
		return

	lock.acquire()
	
	temp = metadata["peer_shares"]

	temp[host] = int(request_value[0])
	
	metadata["peer_shares"] = temp

	lock.release()

#--------------- result view function --------------------

def render_result_page(metadata, lock, conn):

	# http header
	http_response = b"""\
	HTTP/1.1 200 OK

	"""

	tally_result = metadata['tally_result']

	num_candidates = metadata['num_candidates']

	vote_count = {}

	for i in range(len(tally_result)):

		candidate = i % num_candidates

		vote_count[candidate] += int(tally_result[i])

	content = "<table><tr><th>NO. Candidate</th><th>Count of Votes</th></tr>"

	for key in vote_count.keys():

		row = "<tr><td>" + str(key) + "</td><td>" + str(vote_count[key]) + "</td></tr>"

	content += row

	content += '</table>'

	conn.sendall(content.encode())

#------------------ tally function -----------------------

def tally_votes(metadata, lock):

	# tally votes

	tally_result = metadata['masked_vote']

	for peer in metadata['peer_votes'].keys():
		tally_result += metadata['peer_votes'][peer]

	tally_result %= metadata['Zm']

	lock.acquire()

	metadata['tally_result'] = bin(tally_result)[2:].zfill(metadata['vector_len'])

	lock.release()

#------------------ publishe share -----------------------

# broadcast shares to peers
# triggered by signal from peer 0

def publish_shares(metadata, lock, request_value):

	# NOTE: shall we lock it?
	# the shares won't be modified
	# the peer info will not be modified theoretically

	i = 0

	for peer in metadata["peer_info"].keys():

		# ignore the peer if it is not ready (hasn't voted till tally)

		if metadata["peer_info"][peer][1] != "READY":

			continue

		s = socket(AF_INET, SOCK_STREAM)

		# NOTE: what if we run out of sockets?
		# s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

		share = metadata['shares'][i]

		port = metadata["peer_info"][peer][0]

		s.connect((peer, port))

		# enclose information in HTTP packet
		# e.g. /peer?type='share'&value='11'

		packet = "GET /peer_" + str(metadata["node_id"]) + "?type=share&value=" + str(share) + " HTTP/1.1\r\n"

		s.sendall(packet.encode())

		s.close()

		i + 1

#------------------- convert vote ------------------------
# convert local vote into the binary vector
# the binary vector is converted into int

def convert_vote(metadata, lock):

	vector_len = metadata['num_active_peers'] * metadata['num_candidates']

	binary_vector = ['0'] * vector_len

	idx = metadata['node_id'] * metadata['num_candidates'] + metadata['local_vote']

	binary_vector[idx] = '1'

	lock.acquire()

	metadata["convert_vote"] = int(''.join(binary_vector), 2)

	lock.release()
#------------------ generate share -----------------------
	
# generate shares for all peers
def generate_shares(metadata, lock):

	from random import randint

	num_shares = metadata['num_active_peers']

	Zm = metadata['Zm']

	shares = []

	for i in range(num_shares - 1):

		shares.append(randint(0, Zm - 1))

	vote = metadata["convert_vote"]

	private_share = (vote - sum(shares)) % Zm

	shares.append(private_share)

	lock.acquire()

	metadata['shares'] = shares

	lock.release()

#-------------------- mask vote --------------------------

# mask own vote once all shares are received from all peers

def generate_mask_vote(metadata, lock):

	mask = 0

	for peer in metadata['peer_shares'].keys():

		mask += metadata['peer_shares'][peer]

	lock.acquire()

	metadata["masked_vote"] = metadata["shares"][-1] + mask

	lock.release()

#------------------ publish vote -------------------------

# publish vote once all shares from all peers are received

def publish_vote(metadata, lock):

	# send a share to each peer

	vote = metadata["masked_vote"]

	for peer in metadata["peer_info"].keys():

		# pass if the peer hasn't voted

		if metadata["peer_info"][peer][1] != "READY":

			continue

		s = socket(AF_INET, SOCK_STREAM)

		port = metadata["peer_info"][peer][0]

		s.connect((peer, port))

		# enclose information in HTTP packet
		# e.g. /peer?type='share'&value='11'

		packet = "GET /peer_" + str(metadata["node_id"]) + "?type=vote&value=" + str(vote) + " HTTP/1.1\r\n"

		s.sendall(packet.encode())

		s.close()

#--------------- check if all shared ---------------------

# true is all peers' shares received

def all_peers_shared(metadata, lock):

	ready_count = 0
	share_count = 0

	lock.acquire()

	for host in metadata['peer_info'].keys():

		if metadata['peer_info'][host][1] == 'READY':

			ready_count += 1

			if host in metadata['peer_shares']:

				share_count += 1

	lock.release()



	if ready_count == share_count and share_count == len(metadata['peer_shares'].keys()):

		return True

	else:

		return False

#--------------- check if all published ------------------

# true is all peers' votes received

def all_peers_published(metadata, lock):

	ready_count = 0
	published_count = 0

	lock.acquire()

	for host in metadata['peer_info'].keys():

		if metadata['peer_info'][host][1] == 'READY':

			ready_count += 1

			if host in metadata['peer_votes']:

				published_count += 1

	lock.release()

	if ready_count == published_count and published_count == len(metadata['peer_votes'].keys()):

		return True

	else:

		return False

#-------------------- save node id -----------------------

# save number of active nodes, number of candidates, id of the node from peer 0 before generate shares at tally signal received

# "GET /tallyinfo?type=fally&value=num_active_peers&value=num_candidates&value=id"

def save_tally_info(metadata, lock, request_value):

	num_active_peers = int(request_value[0])

	num_candidates = int(request_value[1])

	node_id = int(request_value[2])

	# save following
	# number of active nodes
	# number of candidates
	# node id
	# generate Zm

	lock.acquire()

	metadata["Zm"] = pow(2, num_candidates * num_active_peers) 

	metadata["num_candidates"] = num_candidates

	metadata["num_active_peers"] = num_active_peers

	metadata["node_id"] = node_id

	lock.release()

#-------------------- update status to peer 0 -------------

# once the node has received and save user's vote
# send a status update to peer 0 from ONLINE to READY
def status_update(metadata, lock):

	request = "GET /updatenode?"

	request += "type=update"

	request += "&value=READY"

	request += ' HTTP/1.1\r\n'

	s = socket(AF_INET, SOCK_STREAM)

	s.connect(metadata["peer0"])

	s.sendall(request.encode())

	s.close()












