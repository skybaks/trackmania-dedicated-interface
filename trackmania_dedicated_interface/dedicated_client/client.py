from loguru import logger
import socket
import struct
from xmlrpc.client import dumps, loads, Fault

from .exception import TransportError

class DedicatedClient:
	def __init__(self, host: str, port: int) -> None:
		self.host = host
		self.port = port
		self.protocol = 0
		self.handle = 0

	def get_next_handle(self) -> int:
		if self.handle < 0x80000000 or self.handle >= 0xffffffff:
			self.handle = 0x80000000
			logger.debug('Reset handle to %i' % (self.handle))
		else:
			self.handle += 1
		return self.handle

	def connect(self) -> None:
		logger.info("Connecting to dedicated socket TCP at address %s:%s" % (self.host, self.port))
		self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.client.connect((self.host, self.port))

		resp_bytes = self.client.recv(4)
		(vsize,) = struct.unpack('<1L', resp_bytes)
		if 0 > vsize > 64:
			raise TransportError('wrong lowlevel protocol header')
		resp_bytes = self.client.recv(vsize)
		(header,) = struct.unpack(f'<{len(resp_bytes)}s', resp_bytes)
		header = header.decode()
		logger.debug(header)
		if header == 'GBXRemote 1':
			self.protocol = 1
		elif header == 'GBXRemote 2':
			self.protocol = 2
		else:
			raise TransportError('wrong lowlevel protocol version: %s' % (header))
		logger.info('Using GBXRemote protocol version %i' % (self.protocol))

	def close(self) -> None:
		logger.debug("Closing the connection")
		self.client.close()

	def send_request(self, handle: int, content: str) -> None:
		request_bytes = content.encode()
		length_bytes = len(request_bytes).to_bytes(4, byteorder='little')
		handle_bytes = (handle).to_bytes(4, byteorder='little')
		sent_length = self.client.send(length_bytes + handle_bytes + request_bytes)
		logger.trace('Sent %i bytes' % (sent_length))

	def get_response(self, handle: int) -> str:
		logger.trace('Looking for response with handle: %i' % (handle))
		contents = ''
		while True:
			vsize = 0
			vhandle = 0
			if self.protocol == 1:
				resp_bytes = self.client.recv(4)
				if len(resp_bytes) == 0:
					raise TransportError('cannot read size')
				(vsize,) = struct.unpack('<1L', resp_bytes)
			else:
				resp_bytes = self.client.recv(8)
				if len(resp_bytes) == 0:
					raise TransportError('cannot read size/handle')
				vsize, vhandle = struct.unpack('<2L', resp_bytes)
			logger.trace('Response vsize:%i vhandle:%i' % (vsize, vhandle))

			if vhandle == 0 or vsize == 0:
				raise TransportError('connection interrupted!')
			if vsize > 4096*1024:
				raise TransportError('response too large (%i)' % (vsize))

			contents = ''
			contents_length = 0
			while contents_length < vsize:
				resp_bytes = self.client.recv(vsize-contents_length)
				(resp_str, ) = struct.unpack(f'<{len(resp_bytes)}s', resp_bytes)
				contents += resp_str.decode()
				contents_length = len(contents)
				logger.trace('Received %i bytes' % (len(resp_bytes)))

			if (vhandle & 0x80000000) == 0:
				logger.info('Received callback: %s' % (contents))

			if handle == vhandle:
				break
		return contents

	def query(self, method, *args) -> None:
		handle = self.get_next_handle()
		self.send_request(handle, dumps(args, methodname=method, allow_none=True))
		try:
			(data,), _ = loads(self.get_response(handle))
		except Fault as xmlrpc_fault:
			logger.error(xmlrpc_fault)
			data = None
		return data

class _XmlRpcMethod:
	def __init__(self, method_name: str, method_return: str, method_params: 'list[str]', method_help: str) -> None:
		self.method_name = method_name
		self.method_return = method_return
		self.method_params = method_params
		self.method_help = method_help

class DedicatedCommandClient(DedicatedClient):
	def __init__(self, host: str='127.0.0.1', port: int=5001) -> None:
		super().__init__(host, port)
		self.methods = list()	# type: list[_XmlRpcMethod]

	def populate_methods(self) -> None:
		methods = self.query('system.listMethods')
		for method_name in methods:
			logger.debug('Querying information for method: %s' % (method_name))
			method_signatures = self.query('system.methodSignature', method_name)
			method_help = self.query('system.methodHelp', method_name)
			for signature in method_signatures:
				if len(signature) > 0:
					self.methods.append(_XmlRpcMethod(method_name, signature[0], signature[1:], method_help))
