import urllib, urllib2
from oslo.config import cfg
from oscard import log

oscard_opts = [
	cfg.IntOpt(
		name='proxy_port',
		default=3000,
		help='Oscard proxy port'
	),
	cfg.StrOpt(
		name='proxy_host',
		default='0.0.0.0',
		help='Oscard proxy host'
	),
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
		LOG.info("novapi: create")
		return {"body": "created"}, 200

	def resize(self, **kwargs):
		LOG.info("novapi: resize")
		return {"body": "resized"}, 200

	def destroy(self, **kwargs):
		LOG.info("novapi: destroy")
		return {"body": "destroyed"}, 200

class OscardAPI(CRDAPI):

	# this should be the proxy url
	_baseurl = 'http://' + CONF.proxy_host + ':' + str(CONF.proxy_port)

	def _send_request(self, endpoint='', **kwargs):
		import json, os
		url = os.path.join(self._baseurl, endpoint)
		data = urllib.urlencode(kwargs)
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		return json.loads(response.read())

	def create(self, **kwargs):
		return self._send_request('create', **kwargs)

	def resize(self, **kwargs):
		return self._send_request('resize', **kwargs)

	def destroy(self, **kwargs):
		return self._send_request('destroy', **kwargs)

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

		self.image = nova.images.find(name='cirros') # ['name']
		# assigning all flavors
		self.flavors = {}
		for i in xrange(5):
			self.flavors[i] = nova.flavors.get(i)

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
			instance = nova.servers.get(instance.id)
			status = instance.status
		
		if status == 'ACTIVE':
			# ok the machine is up
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

		return {'resized': id}, 200

	def destroy(self, **kwargs):
		id = kwargs.get('id', None)
		if not id:
			return {'msg': 'id not in kwargs'}, 400

		server = self.nova.servers.get(id)
		server.delete()

		return {'deleted': id}, 204