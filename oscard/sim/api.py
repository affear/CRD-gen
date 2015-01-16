import time
from oslo.config import cfg
from oscard import log

oscard_opts = [
	cfg.StrOpt(
		name='ctrl_host',
		default='localhost',
		help='OpenStack controller host'
	),
	cfg.IntOpt(
		name='keystone_port',
		default=5000,
		help='Keystone port'
	),
	cfg.StrOpt(
		name='os_username',
		default='admin',
		help='OpenStack username (make it match OS conf)'
	),
	cfg.StrOpt(
		name='os_tenant',
		default='admin',
		help='OpenStack tenant name (make it match OS conf)'
	),
	cfg.StrOpt(
		name='os_password',
		default='pwstack',
		help='OpenStack password (make it match OS conf)'
	),
]

CONF = cfg.CONF
CONF.register_opts(oscard_opts)
LOG = log.get_logger(__name__)

class CRDAPI(object):
	_baseurl = 'http://localhost'

	def create(self, **kwargs):
		raise NotImplementedError

	def resize(self, **kwargs):
		raise NotImplementedError

	def destroy(self, **kwargs):
		raise NotImplementedError

class FakeAPI(CRDAPI):

	def create(self, **kwargs):
		from random import randint
		payload = {'id': randint(0, 1000), 'args': kwargs}
		LOG.info('fakeapi: create --> ' + str(payload))
		return payload, 200

	def resize(self, **kwargs):
		payload = {'body': 'resized', 'args': kwargs}
		LOG.info('fakeapi: resize --> ' + str(payload))
		return payload, 200

	def destroy(self, **kwargs):
		payload = {'body': 'destroyed', 'args': kwargs}
		LOG.info('fakeapi: destroy --> ' + str(payload))
		return payload, 200

	@property
	def flavors(self):
		payload = {1: 'tiny', 2: 'small'}
		LOG.info('fakeapi: flavors --> ' + str(payload))
		return payload

from keystoneclient.v2_0 import client as ksclient
from novaclient.v1_1 import client as nvclient
class NovaAPI(CRDAPI):
	_baseurl = 'http://' + CONF.ctrl_host
	_instance_basename = 'fake'

	@property
	def kcreds(self):
		return {
			'username': self._os_username,
			'password': self._os_password,
			'auth_url': self._os_auth_url,
			'tenant_name': self._os_tenant_name
		}

	@property
	def ncreds(self):
		return {
			'username': self._os_username,
			'api_key': self._os_password,
			'auth_url': self._os_auth_url,
			'project_id': self._os_tenant_name
		}
	
	def __init__(self):
		self._curr_id = 0
		self._os_auth_url = self._baseurl + ':' + str(CONF.keystone_port) + '/v2.0'
		self._os_username = CONF.os_username
		self._os_password = CONF.os_password
		self._os_tenant_name = CONF.os_tenant

		self.keystone = ksclient.Client(**self.kcreds)
		self.nova = nvclient.Client(**self.ncreds)

		# assigning to self.image the first cirros image
		# or the first image possible
		images = self.nova.images.list()
		self.image = images[0]
		for img in images:
			if img.name.startswith('cirros'):
				self.image = img
				break

		# assigning all 5 flavors
		self.flavors = {}
		for i in xrange(1, 6):
			self.flavors[i] = self.nova.flavors.get(i)

	def create(self, **kwargs):
		'''
			Creates a new instance.
			This call is blocking untill the instance reaches an ACTIVE status,
			or fails
		'''
		flavor = kwargs.get('flavor', None)
		if not flavor:
			return {'msg': 'flavor not in kwargs'}, 400

		instance = self.nova.servers.create(
			name=self._instance_basename + str(self.curr_id),
			image=self.image,
			flavor=flavor
		)

		# Poll at 2 second intervals, until the status is no longer 'BUILD'
		status = instance.status
		while status == 'BUILD':
			time.sleep(2)
			# Retrieve the instance again so the status field updates
			instance = self.nova.servers.get(instance.id)
			status = instance.status
		
		if status == 'ACTIVE':
			# ok the machine is up
			self._curr_id += 1
			return {'id': instance.id}, 201

		return {'msg': 'error on build', 'status': status}, 400

	def resize(self, **kwargs):
		id = kwargs.get('id', None)
		flavor = kwargs.get('flavor', None)
		if not id:
			return {'msg': 'id not in kwargs'}, 400
		if not flavor:
			return {'msg': 'flavor not in kwargs'}, 400

		server = self.nova.servers.get(id)
		server.resize(flavor)
		server.confirm_resize()

		return {'resized': id}, 200

	def destroy(self, **kwargs):
		id = kwargs.get('id', None)
		if not id:
			return {'msg': 'id not in kwargs'}, 400

		server = self.nova.servers.get(id)
		server.delete()

		return {'deleted': id}, 204