from loguru import logger

def main() -> None:
	from trackmania_dedicated_interface.dedicated_client.client import DedicatedClient
	client = DedicatedClient("127.0.0.1", 5001)
	client.connect()
	#client.query('Authenticate', 'SuperAdmin', 'SuperAdmin')
	methods = client.query('system.listMethods')
	for method in methods[0]:
		method_help = client.query('system.methodHelp', method)
		method_signature = client.query('system.methodSignature', method)
		logger.info('%s(%s) - %s' % (method, method_signature, method_help))
	client.close()

if __name__ == '__main__':
	main()
