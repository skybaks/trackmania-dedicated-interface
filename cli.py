from loguru import logger

def main() -> None:
	from trackmania_dedicated_interface.dedicated_client.client import DedicatedCommandClient
	client = DedicatedCommandClient("127.0.0.1", 5001)
	client.connect()
	client.populate_methods()
	api_version1 = client.query('GetVersion')
	set_api_result = client.query('SetApiVersion', '2022-12-03')
	api_version2 = client.query('GetVersion')
	client.close()

if __name__ == '__main__':
	main()
