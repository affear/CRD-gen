import time, random
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
		payload = {}
		status = 200
		log_level = None
		ok = bool(random.getrandbits(1))

		if ok:
			payload = {'id': random.randint(0, 1000), 'args': kwargs}
			log_level = LOG.info
		else:
			status = 400
			payload = {'msg': 'Random ERROR'}
			log_level = LOG.error

		log_level('fakeapi: create --> ' + str(payload))

		return payload, status

	def resize(self, **kwargs):
		payload = {}
		status = 200
		log_level = None
		ok = bool(random.getrandbits(1))

		if ok:
			payload = {'body': 'resized', 'args': kwargs}
			log_level = LOG.info
		else:
			status = 400
			payload = {'msg': 'Random ERROR'}
			log_level = LOG.error

		log_level('fakeapi: resize --> ' + str(payload))

		return payload, status

	def destroy(self, **kwargs):
		payload = {}
		status = 200
		log_level = None
		ok = bool(random.getrandbits(1))

		if ok:
			payload = {'body': 'destroyed', 'args': kwargs}
			log_level = LOG.info
		else:
			status = 400
			payload = {'msg': 'Random ERROR'}
			log_level = LOG.error

		log_level('fakeapi: destroy --> ' + str(payload))

		return payload, status

	def is_smart(self):
		return {'smart': False}, 200

	def snapshot(self):
		metrics = {
			'vcpus': '?',
			'vcpus_used': '?',
			'memory_mb': '?',
			'memory_mb_used': '?'
		}

		return {
			'fakehost1': metrics,
			'fakehost2': metrics
		}, 200

from keystoneclient.v2_0 import client as ksclient
from novaclient.v1_1 import client as nvclient
from novaclient.exceptions import NotFound
class NovaAPI(CRDAPI):
	_baseurl = 'http://' + CONF.ctrl_host
	_instance_basename = 'fake'
	_TIMEOUT = 10 # preventing deadlocks
	_POLL_TIME = 0.5 # polling time

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

	@property
	def server_ids(self):
		servers = self.nova.servers.list()
		return [s.id for s in servers]
	
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
		flavor_id = random.choice(self.flavors.keys())
		flavor = self.flavors[flavor_id]

		instance = self.nova.servers.create(
			name=self._instance_basename + str(self._curr_id),
			image=self.image,
			flavor=flavor
		)

		# Poll at 1 second intervals, until the status is no longer 'BUILD'
		waiting_time = 0
		status = instance.status
		while status == 'BUILD' and waiting_time < self._TIMEOUT:
			time.sleep(self._POLL_TIME)
			waiting_time += 1
			# Retrieve the instance again so the status field updates
			instance = self.nova.servers.get(instance.id)
			status = instance.status
		
		if status == 'ACTIVE':
			# ok the machine is up
			self._curr_id += 1
			return {'id': instance.id}, 201

		return {'msg': 'error on build', 'status': status}, 400

	def resize(self, **kwargs):
		'''
			Blocking call untill the resize has been confirmed
			and the instance is in status ACTIVE
		'''
		
		id = random.choice(self.server_ids)
		server = self.nova.servers.get(id)

		# remove the already chosen flavor from
		# flavors ids
		flavors_ok = self.flavors.keys()
		flavors_ok.remove(int(server.flavor['id']))
		flavor_id = random.choice(flavors_ok)

		flavor = self.flavors[flavor_id]
		server.resize(flavor)

		waiting_time = 0
		status = server.status
		while status != 'VERIFY_RESIZE' and waiting_time < self._TIMEOUT:
			time.sleep(self._POLL_TIME)
			waiting_time += 1
			# Retrieve the instance again so the status field updates
			server = self.nova.servers.get(server.id)
			status = server.status

		if status != 'VERIFY_RESIZE' and waiting_time == self._TIMEOUT:
			return {'msg': 'timeout exceeded on resize'}, 400

		server.confirm_resize()

		waiting_time = 0
		status = server.status
		while status != 'ACTIVE' and waiting_time < self._TIMEOUT:
			time.sleep(self._POLL_TIME)
			waiting_time += 1
			server = self.nova.servers.get(server.id)
			status = server.status

		if status != 'ACTIVE' and waiting_time == self._TIMEOUT:
			return {'msg': 'timeout exceeded on confirm_resize'}, 400

		return {'id': id}, 200

	def destroy(self, **kwargs):
		id = random.choice(self.server_ids)

		server = self.nova.servers.get(id)
		server.delete()

		while True:
			time.sleep(self._POLL_TIME)
			try:
				self.nova.servers.get(id)
			except NotFound:
				# this means that the server is not found,
				# so it has been really deleted!
				break

		return {'id': id}, 200

	def snapshot(self):
		ans = {}
		hosts = self.nova.hypervisors.list()
		# retrieve only active hosts
		hosts = filter(lambda h: h.vcpus_used != 0, hosts)

		#####
		# if you want to retrieve the host from the server:
		#
		# instance = api.nova.servers.list()[0]
		# hostname = getattr(instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname')
		# host = api.nova.hypervisors.find(hypervisor_hostname=hostname)
		#####

		for h in hosts:
			ans[h.hypervisor_hostname] = {
				'vcpus': h.vcpus,
				'vcpus_used': h.vcpus_used,
				'memory_mb': h.memory_mb,
				'memory_mb_used': h.memory_mb_used,
			}
		return ans, 200

	def is_smart(self):
		services = self.nova.services.list()
		names = [s.binary for s in services]
		return {'smart': 'nova-consolidator' in names}, 200