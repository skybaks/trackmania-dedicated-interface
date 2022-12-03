
class DedicatedClientException:
	pass

class TransportError(DedicatedClientException):
	def __init__(self, message: str) -> None:
		super().__init__('Transport Error - %s' % (message))
