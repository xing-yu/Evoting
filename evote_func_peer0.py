


#--------------------------- handle a request ----------------------------

def handle_request(parsed_request, conn, addr, lock, meta_data):

	if addr[0] == meta_data["host"]:

		handle_local_request(parsed_request, conn, lock, meta_data)

	else:

		handle_peer_request(parsed_request, conn, addr, lock, meta_data)


#-------------------------- handle peer requests -------------------------

def handle_peer_request(parsed_request, conn, addr, lock, meta_data):

	from urllib.parse import urlparse
    from urllib.parse import parse_qs

    q = parse_qs(urlparse(parsed_request[1]).query)

    # registration request

    if q['type'][0] == 'registration':

    	# this is a registration request from a new node

    	lock.acquire()

    	if addr[0] not in meta_data["node_info"]:

            meta_data["node_info"][addr][0] = (q['value'][0], 'ONLINE', meta_data['cur_id'])

            conn.sendall(str(meta_data['cur_id']).encode())

            meta_data['cur_id'] += 1

        lock.release()

    elif q['type'][0] == 'vote':

        lock.acquire()

        if addr[0] not in meta_data["node_info"]:

        





    		





