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

	# peer information, {ip : (port, status)}
	server.metadata['peer_info'] = {}

	# peer votes, {ip : vote}
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

	# [int]
	# value of the sumation of all votes from all nodes
	# value -> binary vector
	# a vector of vote count for candidates
	server.metadata['tally_result'] = None

	# int
	# number of active peers at tally
	server.metadata['num_active_peers'] = None

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
				render_result_page(metadata, conn)

			# return waiting page
			else:

				render_page(metadata, conn, waiting_file)

		# save local user vote
		elif request_type == 'vote' and metadata['local_vote'] == None:

			save_user_vote(metadata, request_value)

		# return voting page
		elif metadata['local_vote'] == None and request_type == None:

			# unique view, need to implement individually
			render_page(metadata, conn, vote_file)

	# host requests
	elif host == metadata['peer0'][0]

		# start tally
		if request_type == 'tally':

			publish_shares(metadata, request_value)

		# save node id assigned by peer 0
		elif request_type == 'id':

			save_node_id(metadata, request_value)

		# update peer information from peer 0
		elif request_type == 'updates':

			update_peer_info(metadata, request_value)

	# peer requests
	else:

		# save share from a peer
		if request_type == 'share':

			save_peer_share(metadata, request_value)

			# if all shares received
			if all_peers_shared(metadata):

				# mask local vote
				create_mask_vote(metadata)

				# publish vote
				publish_vote(metadata)

		# save vote from a peer
		elif request_type == 'vote':

			save_peer_vote(metadata, request_value)

			# if all vote received
			if all_peers_published(metadata):

				# tally result
				tally_votes(metadata)

				# show tally result
				render_page(metadata, conn, 'tally')

	# close connection
	conn.close()

#-------------------------- handle local request (sub) ---------------------------
def handle_local_request(parsed_request, conn, peer_0, meta_data):

	from urllib.parse import urlparse
    from urllib.parse import parse_qs

	# if the local peer has not voted

	if meta_data["local_vote"] == None:

		# get vote information from the request

		q = parse_qs(urlparse(parsed_request[1]).query)

		# return vote page
		# if vote information is missing

		if 'vote' not in q:

			response = vote_view(vote_page)

			conn.sendall(response)

			conn.close()

		# save vote value

		else:

			lock.acquire()

			meta_data["local_vote"] = int(q['vote'][0])

			lock.release()

			# return success message

			response = b"""\
			HTTP/1.1 200 OK

			Hi there, your vote is received!

			"""

			conn.sendall(response)

			conn.close()

			# TODO: send status update to peer 0 from ready to voted

	# revoting is not allowed

	else:

		# return success message

		response = b"""\
		HTTP/1.1 200 OK

		Hi there, your vote is received!

		"""

		conn.sendall(response)

		conn.close()

#-------------------------- handle peer request (sub) ----------------------------
def handle_peer_request(parsed_request, conn, addr, lock, meta_data):

	# use http protocol among peers
	# information stored as queries in path

	# queries
	# type: can be either share or vote
	# value: the value of the share or vote
	# e.g. /peer?type='share'&value='11'
	
	from urllib.parse import urlparse
    from urllib.parse import parse_qs

	q = parse_qs(urlparse(parsed_request[1]).query)

	# if it's a share

	if q['type'][0] == 'share':

		# TODO: create a function that retrieve the list of peers from peer_0
		# as part of the server initialization
		# may not need to acquire that
		# just keep a record  of the peers

		# mark the peer as shared, using ip as peer id
		# save the shared value

		lock.acquire()

		if addr[0] not in meta_data['peer_shares']:

			meta_data['peer_shares'][addr[0]] = int(q['value'][0])

		lock.release()

		# publish if all shares received
		if len(meta_data["peer_info"].keys()) == len(meta_data["peer_shares"].keys()):

			publish_vote(meta_data)

	# if the peer is publishing its vote
	elif q['type'][0] == 'vote':

		lock.acquire()

		if addr[0] not in meta_data["peer_votes"]:

			meta_data["peer_votes"][addr[0]] = int(q['value'][0])

		lock.release()

		# tally if all votes are published

		if len(meta_data["peer_info"].keys()) == len(meta_data["peer_votes"].keys()) and len(meta_data["peer_info"].keys()) == len(meta_data["peer_shares"].keys()):

			tally(lock, meta_data)

#---------------------------- vote view function (sub) ---------------------------

def vote_view(html_file):

	# http header
	http_response = b"""\
	HTTP/1.1 200 OK

	"""

	# html file for the view
	f = open(html_file, 'r')

	# read and load content
	content = f.read()
	f.close()

	http_response = http_response + content

	return http_response.encode()

#--------------------------- tally view function ----------------------------------

def tally_view(html_file, meta_data):
	
	# if environ["tallied"] is true
	# return tallied result

	if meta_data["tally_result"] == None:

		return

	# http header
	http_response = b"""\
	HTTP/1.1 200 OK

	"""

	# html file for the view
	f = open(html_file, 'r')

	# read and load content
	content = f.read()
	f.close()

	# TODO: enclose tally_result with tags
	http_response = http_response + content + tally_result

	return http_response.encode()

#---------------------------- tally function --------------------------------------

def tally(lock, meta_data):
	
	# if already tallied

	if meta_data['tally_result'] != None:

		return

	# tally votes

	tally_result = 0

	for ip in meta_data['peer_votes'].keys():
		tally_result += meta_data['peer_votes'][ip]

	# TODO: calculate Zm, and voting vector length in publish share function

	tally_result %= meta_data['Zm']

	if meta_data["masked_vote"] == None:

		mask_vote(meta_data)

	tally_result += meta_data["masked_vote"]

	# Note: vector_len = cadidate_num * voter_num

	lock.acquire()

	meta_data['tally_result'] = bin(tally_result)[2:].zfill(meta_data['vector_len'])

	lock.release()

#---------------------------- broadcast share -------------------------------------

# broadcast shares to peers
# triggered by signal from peer 0

def broadcast_shares(lock, meta_data):
	
	# generate shares 
	gen_shares(lock, meta_data)

	# TODO: prevent duplicated import
	from socket import *

	i = 0

	for peer in meta_data["peer_info"].keys():

		# ignore the peer if it is not ready (hasn't voted till tally)

		if meta_data["peer_info"][peer][1] != "READY":

			continue

		s = socket(AF_INET, SOCK_STREAM)

		s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

		share = meta_data['shares'][i]

		port = meta_data["peer_info"][peer][0]

		s.connect((peer, port))

		# enclose information in HTTP packet
		# e.g. /peer?type='share'&value='11'

		packet = "GET /peer_" + str(meta_data["node_id"]) + "?type=share&value=" + str(share) + " HTTP/1.1\r\n"

		s.sendall(packet.encode())

		s.close()

		i + 1

#----------------------------- generate share -------------------------------------
	
# generate shares for all peers
def gen_shares(lock, meta_data):

	# return if the client hasn't voted

	from random import randint

	num_shares = meta_data['num_active_peers']

	Zm = meta_data['Zm']

	shares = []

	for i in range(num_shares - 1):

		shares.append(randint(0, Zm - 1))

	vote = meta_data["convert_vote"]

	private_share = (vote - sum(shares)) % Zm

	shares.append(private_share)

	lock.acquire()

	meta_data['shares'] = shares

	lock.release()

#---------------------------- mask vote -------------------------------------------

# mask own vote once all shares are received from all peers

def mask_vote(lock, meta_data):

	# return if not everyone has voted

	mask = 0

	for peer in meta_data['peer_shares'].keys():

		mask += meta_data['peer_shares'][peer]

	lock.acquire()

	meta_data["masked_vote"] = meta_data["shares"][-1] + mask

	lock.release()

#---------------------------- publish vote ----------------------------------------

# publish vote once all shares from all peers are received

def publish_vote(lock, meta_data):
	
	# TODO: check how to avoid duplicated import
	from socket import *

	if meta_data["masked_vote"] == None:
		mask_vote(lock, meta_data)


	# send a share to each peer

	vote = meta_data["mask_vote"]

	for peer in meta_data["peer_info"].keys():

		# pass if the peer hasn't voted

		if meta_data["peer_info"][peer][1] != "READY":

			continue

		s = socket(AF_INET, SOCK_STREAM)

		port = meta_data["peer_info"][peer][0]

		s.connect((peer, port))

		# enclose information in HTTP packet
		# e.g. /peer?type='share'&value='11'

		packet = "GET /peer_" + str(meta_data["node_id"]) + "?type=vote&value=" + str(vote) + " HTTP/1.1\r\n"

		s.sendall(packet.encode())

		s.close()





