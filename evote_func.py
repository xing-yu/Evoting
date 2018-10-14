# The Evote application
# Written in functions for multiprocessing

# macros

vote_page = ""	# html file for rendering the voting page
tally_page = "" # html file for rendering the tally page

#--------------------------- handle a single request ------------------------------

def handle_request(parsed_request, conn, addr, lock, environ):

	# parsed_request: (method, path, version)
	# conn: socket connection
	# addr: client address (ip, port)
	# lock: semaphone

	from urllib.parse import urlparse
    from urllib.parse import parse_qs

	# handle local request
	if addr[0] = '127.0.0.1':

		# call sub-function to handle a local request

		handle_local_request(parsed_request, conn, lock, environ)	

	# handle peer request
	else:

		# call sub-function to handle a peer request
		handle_peer_request(parsed_request, conn, addr, lock, environ)

#-------------------------- handle local request (sub) ---------------------------
def handle_local_request(parsed_request, conn, peer_0, environ):

	# if the local peer has not voted

	if environ['client_has_voted'] == False:

		# get vote information from the request

		q = parse_qs(urlparse(parsed_request[1]).query)

		# return vote page
		# if vote information is missing

		if 'vote' not in q:

			response = vote_view(vote_page)

			conn.sendall(response)

		# save vote value

		else:

			# lock environ before writing

			lock.acquire()

			environ['client_has_voted'] = True

			lock.release()

			# TODO: move the gen_vote to the server class
			# which should be triggered by peer 0

			# environ['self_vote'] = gen_vote(q['vote'])

			# TODO: move the broadcast process to the server class
			# which is also triggered by peer 0

			# broadcast_shares(environ['self_vote'])

	# if the local peer has voted
	# new vote information(if any) will be ignored
	# TODO: think about the question - should revote be allowed?
	# maybe not for now

	else:

		# generate tally view

		response = tally_view(environ)

		conn.sendall(response)

#-------------------------- handle peer request (sub) ----------------------------
def handle_peer_request(parsed_request, conn, addr, lock, environ):

	# use http protocol among peers
	# information stored as queries in path

	# queries
	# type: can be either share or vote
	# value: the value of the share or vote
	
	q = parse_qs(urlparse(parsed_request[1]).query)

	# if it's a share

	if q['type'][0] == 'share':

		# TODO: create a function that retrieve the list of peers from peer_0
		# as part of the server initialization
		# may not need to acquire that
		# just keep a record  of the peers

		# mark the peer as shared, using ip as peer id
		# save the shared value

		# TODO: lock to modify
		# environ['remaining_not_shared'] is the number of peers that haven't shared

		if addr[0] not in environ['peer_has_shared']:

			environ['peer_has_shared'][addr[0]] = True
			environ['peer_shares'][addr[0]] = q['value'][0]
			environ['remaining_not_shared'] -= 1

		# TODO: unlock after this point

		# TODO: check if all peers have shared
		# TODO: implement the publish function

		if environ['remaining_not_shared'] == 0:
			publish()

	# if the peer is publishing its vote
	elif q['type'][0] == 'vote':

		if environ['peer_has_published'][addr[0]] == False:

			# TODO: lock

			environ['peer_has_published'][addr[0]] = True
			environ['peer_votes'][addr[0]] = q['vote'][0]
			environ['remaining_not_published'] -= 1

			# TODO: unlock

		# tally if all votes are published
		# TODO: implement tally function

		if environ['remaining_not_published'] == 0:
			tally()

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

def tally_view(html_file, environ):
	
	# if environ["tallied"] is true
	# return tallied result

	if environ['tallied'] == True:

		tally_result = environ['tally_result']

	# try tally first
	else:
		tally_result = None

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

def tally(environ):
	
	# if already tallied

	if environ['tallied'] == True:

		return

	# if peers haven't submitted all votes

	if environ['remaining_not_published'] > 0 or if environ['remaining_not_shared'] > 0:

		return 

	# tally votes

	tally_total = 0

	for ip in environ['peer_votes'].keys():
		tally_total += int(environ['peer_votes'][ip])

	tally_total %= environ['zm']

	# TODO: plus own_vote_masked
	# TODO: lock
	# Note: vector_len = cadidate_num * voter_num

	environ['tally_result'] = bin(tally_total)[2:].zfill(environ['vector_len'])
	environ['tallied'] = True

#---------------------------- broadcast share -------------------------------------

# broadcast shares of vote after receiving vote from the local peer
def broadcast_shares(environ):
	
	# return if shares do not exist
	if "shares" not in environ:
		return

	# TODO: prevent duplicated import
	from socket import *

	i = 0
	l = environ['num_peers']

	while i < l:
		s = socket(AF_INET, SOCK_STREAM)

		share = environ['shares'][i]

		peer = environ['peers'][i]

		s.connect(peer)

		# TODO: enclose share in http

		s.sendall(share.encode())

		s.close()

		i + 1

#----------------------------- generate share -------------------------------------
	
# generate shares for all peers
def gen_shares(environ):

	# return if the client hasn't voted
	
	if environ['client_has_voted'] == False:
		return

	from random import randint

	num_shares = environ['num_peers']

	# TODO: predefine Zm in server initalization

	zm = environ['zm']

	shares = []

	for i in range(num_shares - 1):
		shares.append(randint(0, zm - 1))

	private_share = (int(environ['self_vote']) - sum(shares)) % zm

	# TODO: lock
	environ['shares'] = shares
	environ['private_share'] = private_share
	# TODO: unlock

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




