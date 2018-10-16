# The Evote application
# Written in functions for multiprocessing

# macros

vote_page = ""	# html file for rendering the voting page
tally_page = "" # html file for rendering the tally page
vote_success_page = "" # html file to show user that vote is successfully received

# vote page should have one form
# action = "submitVote"
# query name = "vote"
# query value = [the vote]
# e.g., /submitVote?vote=1

#--------------------------- handle a single request ------------------------------

def handle_request(parsed_request, conn, addr, lock, meta_data):

	# parsed_request: (method, path, version)
	# conn: socket connection
	# addr: client address (ip, port)
	# lock: semaphone

	from urllib.parse import urlparse
    from urllib.parse import parse_qs

	# handle local request
	if addr[0] = '127.0.0.1':

		handle_local_request(parsed_request, conn, lock, meta_data)	

	# handle peer request
	else:

		handle_peer_request(parsed_request, conn, addr, lock, meta_data)

#-------------------------- handle local request (sub) ---------------------------
def handle_local_request(parsed_request, conn, peer_0, meta_data):

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

			# lock environ before writing

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

		s = socket(AF_INET, SOCK_STREAM)

		s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

		share = meta_data['shares'][i]

		s.connect(peer)

		# TODO: enclose share in http
		# e.g. /peer?type='share'&value='11'

		packet = "GET /peer" + str(meta_data["node_id"]) + "?type=share&value=" + str(share) + " HTTP/1.1\r\n"

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

def mask_vote(environ):

	# return if not everyone has voted

	if environ['remaining_not_shared'] > 0:
		return

	# read and add shares

	mask = 0

	for peer in environ['peer_shares'].keys():

		mask += int(environ['peer_shares'][peer])

	# TODO: lock environ

	environ["vote_masked"] = environ["private_share"] + mask

	# TODO: unlock

#---------------------------- publish vote ----------------------------------------

# publish vote once all shares from all peers are received

def publish_vote(environ):
	
	# TODO: check how to avoid duplicated import
	from socket import *

	# return if vote is not masked

	if "vote_masked" not in environ:
		return


	# send a share to each peer
	l = environ['num_peers']

	i = 0

	vote = environ["vote_masked"]

	while i < l:

		s = socket(AF_INET, SOCK_STREAM)

		peer = environ['peers'][i]

		s.connect(peer)

		# TODO: enclose vote in http

		s.sendall(share.encode())

		s.close()

		i += 1




