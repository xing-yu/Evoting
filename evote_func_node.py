# The Evote application
# Written in functions for multiprocessing

from utility import *

# macros

vote_file = ""	# html file for rendering the voting page
waiting_file = "" # html file to show user that vote is successfully received

# vote page should have one form
# action = "submitVote"
# query name = "vote"
# query value = [the vote]
# e.g., /submitVote?vote=1

#--------------------------- init metadata ----------------------------

def init_metadata(server):

	from multiprocessing import *

	server.metadata = Manager.dict()

	# host ip address, str
	server.metadata['host'] = ''

	# server port, int
	server.metadata['port'] = 9999

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
	# Zm = 2**vector_len + 1
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

#--------------------------- identify request ------------------------

def handle_request(parsed_request, conn, addr, lock, metadata):

	from urllib.parse import urlparse
    from urllib.parse import parse_qs

    # queries
    q = parse_qs(urlparse(parsed_request[1]).query)

    # request source
	host = addr[0]

	# request type
	request_type = q['type'][0]

	# request value
	request_value = q['value']

	# local requests

	if host == '127.0.0.1':

		if metadata['local_vote'] != None:

			# return tally result page
			if metadata['tally_result'] == None:

				# unique view, need to implement individually

				# TODO: implement
				render_result_page(metadata, lock)

			# return waiting page
			else:

				render_page(conn, waiting_file)

		# save local user vote
		elif request_type == 'vote' and metadata['local_vote'] == None:

			# save local user's vote
			save_user_vote(metadata, lock, host, request_value)

		# return voting page
		elif metadata['local_vote'] == None and request_type == None:

			# unique view, need to implement individually
			render_page(conn, vote_file)

	# host requests
	elif host == metadata['peer0'][0]

		# start tally
		if request_type == 'tally':

			# generate shares and publish to all active peers
			convert_vote(metadata, lock)

			generate_shares(metadata, lock)

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
			save_peer_share(metadata,lock, host, request_value)

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

#-------------------------- register function -----------------------
# this function register node with peer 0
def register(metadata):
	from socket import *
    import sys

    # initialize a socket to send node info to peer 0
    # peer 0 must be working

    s = socket(AF_INET, SOCK_STREAM)

    try:
            
        s.connect(self.metadata['peer0'])
        
    except:

        print("Cannot connect to peer 0 due to failure of creating a socket!")

        sys.exit(-1)

    # create a request to send port information to peer 0

    request = "GET /nodeinfo?"

    request += 'type=registration&'

    request += 'value=' + str(self.metadata['port'])

    request += 'HTTP/1.1\r\n'

    s.sendall(request.encode())

    node_id = s.recv(1024).decode()

    self.metadata["node_id"] = int(node_id)

    print("Node registration is successful! The node id is " + node_id)

    s.close()    

#--------------------------- updates peer info ----------------------
# update peer status from peer 0
# request value: [ip, status, ip, status, ...]
def update_peer_info(metadata, lock, request_value):

	host, status = None, None

	for idx, value in enumerate(request_value):
		if idx % 2 == 0:
			host = value
		else:
			status = value

			lock.acquire()

			metadata['peer_info'][host][1] = status

			lock.release()
	
#------------------------- save user vote ---------------------------
# save local user's vote
# the number indicates which candidate the user voted for
def save_user_vote(metadata, lock, request_value):

	lock.acquire()

	metadata["local_vote"] = int(request_value[0])

	lock.release()

#------------------------- save peer vote ---------------------------
# request_value: [value]
def save_peer_vote(metadata, lock, host, request_value):

	# if the source is not valid, ignore
	if metadata["peer_info"][host][1] != 'READY' or host not in metadata["peer_info"]:
		return

	lock.acquire()

	metadata["peer_votes"][host] = int(request_value[0])

	lock.release()

#------------------------- save peer share --------------------------
# request_value: [value]
def save_peer_share(metadata, lock, host, request_value):

	# if the source is not valid, ignore
	if metadata['peer_info'][host][1] != 'READY' or host not in metadata['peer_info']:
		return

	lock.acquire()

	metadata['peer_shares'][host] = int(request_value[0])

	lock.release()

#------------------------- tally view function ----------------------

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

#---------------------- tally function ------------------------------

def tally_votes(metadata, lock):

	# tally votes

	tally_result = metadata['masked_vote']

	for peer in metadata['peer_votes'].keys():
		tally_result += metadata['peer_votes'][peer]

	tally_result %= metadata['Zm']

	lock.acquire()

	metadata['tally_result'] = bin(tally_result)[2:].zfill(metadata['vector_len'])

	lock.release()

#------------------------- publishe share ---------------------------

# broadcast shares to peers
# triggered by signal from peer 0

def publish_shares(metadata, lock, request_value):

	# NOTE: shall we lock it?
	# the shares won't be modified
	# the peer info will not be modified theoretically

	from socket import *

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

#------------------------- convert vote -----------------------------
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
#------------------------- generate share ---------------------------
	
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

#-------------------------- mask vote -------------------------------

# mask own vote once all shares are received from all peers

def generate_mask_vote(metadata, lock):

	mask = 0

	for peer in metadata['peer_shares'].keys():

		mask += metadata['peer_shares'][peer]

	lock.acquire()

	metadata["masked_vote"] = metadata["shares"][-1] + mask

	lock.release()

#------------------------ publish vote ------------------------------

# publish vote once all shares from all peers are received

def publish_vote(metadata, lock):
	
	from socket import *

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

#------------------------- check if all shared ----------------------

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

#-------------------------- check if all published ------------------

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








