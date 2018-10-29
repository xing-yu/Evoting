# utility functions

#------------------- render page --------------------------

def render_page(conn, file):

	header = """HTTP/1.1 200 OK

		"""
	try:
		content = open(file, 'r').read()

	except:

		print("Cannot open GUI files.")

	response = header + content  + '''

	'''

	# print(response)

	conn.sendall(response.encode())
	print(file)

	print("Done sending response!")