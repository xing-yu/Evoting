# utility functions

#------------------- render page --------------------------

def render_page(metadata, conn, file):

	header = b"""\
		HTTP/1.1 200 OK

		"""

	content = open(file, 'r').read()

	response = header + content  + '''

	'''

	conn.sendall(response.encode())

def public(metadata, type):

	

