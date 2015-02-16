import time
from oslo.config import cfg
from oscard import log
from oscard import randomizer

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

def return_code(code):
	def wrapped0(fun):
		def wrapped1(*args, **kwargs):
			res = fun(*args, **kwargs)
			if type(res) is not tuple:
				return res, code
			return res
		return wrapped1

	return wrapped0

def reraise_as_400(fun):
	def wrapped(*args, **kwargs):
		try:
			return fun(*args, **kwargs)
		except Exception as e:
			return {'msg': e.message}, 400
	return wrapped

class CRDAPI(object):
	_baseurl = 'http://localhost'

	def create(self, **kwargs):
		raise NotImplementedError

	def resize(self, **kwargs):
		raise NotImplementedError

	def destroy(self, **kwargs):
		raise NotImplementedError

class FakeAPI(CRDAPI):
	rnd = randomizer.get_randomizer()

	def init(self, **kwargs):
		self.rnd = randomizer.get_randomizer()
		seed = randomizer.get_seed()
		return {'seed': seed}, 200

	def create(self, **kwargs):
		payload = {}
		status = 200
		log_level = None
		ok = bool(self.rnd.getrandbits(1))

		if ok:
			payload = {'id': self.rnd.randint(0, 1000), 'args': kwargs}
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
		ok = bool(self.rnd.getrandbits(1))

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
		ok = bool(self.rnd.getrandbits(1))

		if ok:
			payload = {'body': 'destroyed', 'args': kwargs}
			log_level = LOG.info
		else:
			status = 400
			payload = {'msg': 'Random ERROR'}
			log_level = LOG.error

		log_level('fakeapi: destroy --> ' + str(payload))

		return payload, status

	def active_services(self):
		services = ['fakeservice1', 'fakeservice2']
		data = {}
		for i, s in enumerate(services):
			data[i] = {
				'binary': s,
				'n': self.rnd.randint(1, 42)
			}

		return data, 200

	@property
	def architecture(self):
		arch = {}
		arch[0] = {
			'hostname': 'fakehost0',
			'address': '42.42.42.2',
			'vcpus': '??',
			'memory_mb': '??',
			'local_gb': '??',
		}

		arch[1] = {
			'hostname': 'fakehost1',
			'address': '42.42.42.4',
			'vcpus': '??',
			'memory_mb': '??',
			'local_gb': '??',
		}

		return arch, 200

	def snapshot(self):
		metrics = {
			'vcpus_used': '?',
			'memory_mb_used': '?',
			'local_gb_used': '?',
			'r_vcpus': '?',
			'r_memory_mb': '?',
			'r_local_gb': '?'
		}

		hosts = {}

		metrics['hostname'] = 'fakehost0'
		metrics['address'] = '42.42.42.2'
		hosts[0] = metrics
		metrics['hostname'] = 'fakehost1'
		metrics['address'] = '42.42.42.4'
		hosts[1] = metrics

		return {
			'cmps': hosts,
			'avg_r_vcpus' : 0,
			'avg_r_memory_mb' : 0,
			'avg_r_local_gb' : 0,
			'no_active_cmps': 2
		}, 200

from keystoneclient.v2_0 import client as ksclient
from novaclient.v1_1 import client as nvclient
from novaclient.exceptions import NotFound
class NovaAPI(CRDAPI):
	_baseurl = 'http://' + CONF.ctrl_host
	_instance_basename = 'fake'
	_TIMEOUT = 20 # preventing deadlocks
	_POLL_TIME = 0.5 # polling time
	# statuses
	_ACTIVE_STATUS = 'ACTIVE'
	_VERIFY_RESIZE_STATUS = 'VERIFY_RESIZE'
	_ERROR_STATUS = 'ERROR'
	_TIMEOUT_EXCEEDED_STATUS = 'TIMEOUT_EXCEEDED'

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
	@reraise_as_400
	def server_ids(self):
		servers = self.nova.servers.list()
		return [s.id for s in servers]

	@property
	@reraise_as_400
	@return_code(200)
	def architecture(self):
		arch = {}
		cmps = self.nova.hypervisors.list()

		for c in cmps:
			# update known cmps.
			# append new ones at the end of the list.
			# in this way a cmp will always be in the same position of the list.
			if not c.host_ip in self._known_cmps:
				self._known_cmps.append(c.host_ip)

			cmp_index = self._known_cmps.index(c.host_ip)
			arch[cmp_index] = {
				'hostname': c.hypervisor_hostname,
				'address': c.host_ip,
				'vcpus': c.vcpus,
				'memory_mb': c.memory_mb,
				'local_gb': c.local_gb,
			}
				
		return arch
	
	def __init__(self):
		self._rnd = randomizer.get_randomizer()
		self._curr_id = 0
		self._os_auth_url = self._baseurl + ':' + str(CONF.keystone_port) + '/v2.0'
		self._os_username = CONF.os_username
		self._os_password = CONF.os_password
		self._os_tenant_name = CONF.os_tenant

		self.keystone = ksclient.Client(**self.kcreds)
		self.nova = nvclient.Client(**self.ncreds)

		cmps = self.nova.hypervisors.list()
		self._known_cmps = [c.host_ip for c in cmps] 

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

	def _until_timeout(self, server, wanted_status='ACTIVE'):
		waiting_time = 0
		status = server.status
		while status != wanted_status and waiting_time < self._TIMEOUT:
			if status == self._ERROR_STATUS:
				break

			time.sleep(self._POLL_TIME)
			waiting_time += 1
			# Retrieve the instance again so the status field updates
			server = self.nova.servers.get(server.id)
			status = server.status

		if waiting_time == self._TIMEOUT:
			status = self._TIMEOUT_EXCEEDED_STATUS

		return status

	def _get_random_active_server(self):
		ids = list(self.server_ids) #copy ids

		id = self._rnd.choice(ids)
		server = self.nova.servers.get(id)

		while server.status != self._ACTIVE_STATUS:
			ids.remove(id)
			id = self._rnd.choice(ids)
			server = self.nova.servers.get(id)

		if server.status == self._ACTIVE_STATUS:
			return server
		return None

	@reraise_as_400
	@return_code(200)
	def init(self, **kwargs):
		self._rnd = randomizer.get_randomizer()
		return {'seed': randomizer.get_seed()}

	@reraise_as_400
	@return_code(201)
	def create(self, **kwargs):
		'''
			Creates a new instance.
			This call is blocking untill the instance reaches an ACTIVE status,
			or fails
		'''
		flavor_id = self._rnd.choice(self.flavors.keys())
		flavor = self.flavors[flavor_id]

		server = self.nova.servers.create(
			name=self._instance_basename + str(self._curr_id),
			image=self.image,
			flavor=flavor
		)

		status = self._until_timeout(server)

		if status == self._TIMEOUT_EXCEEDED_STATUS:
			raise Exception('timeout exceeded on create')
		
		if status == self._ACTIVE_STATUS:
			# ok the machine is up
			self._curr_id += 1
			return {'id': server.id}

		# there was a failure in OpenStack
		server = self.nova.servers.get(id)
		raise Exception(server.fault.get('message', ''))

	@reraise_as_400
	@return_code(200)
	def resize(self, **kwargs):
		'''
			Blocking call untill the resize has been confirmed
			and the instance is in status ACTIVE
		'''
		
		server = self._get_random_active_server()

		if server is None:
			raise Exception('No ACTIVE server found')

		# remove the already chosen flavor from
		# flavors ids
		flavors_ok = self.flavors.keys()
		flavors_ok.remove(int(server.flavor['id']))
		flavor_id = self._rnd.choice(flavors_ok)

		flavor = self.flavors[flavor_id]
		server.resize(flavor)

		status = self._until_timeout(server, wanted_status='VERIFY_RESIZE')

		if status == self._TIMEOUT_EXCEEDED_STATUS:
			raise Exception('timeout exceeded on resize')

		if status == self._ERROR_STATUS:
			server = self.nova.servers.get(id)
			raise Exception(server.fault.get('message', ''))

		server.confirm_resize()

		status = self._until_timeout(server)

		if status == self._TIMEOUT_EXCEEDED_STATUS:
			raise Exception('timeout exceeded on confirm_resize')

		if status == self._ERROR_STATUS:
			server = self.nova.servers.get(id)
			raise Exception(server.fault.get('message', ''))

		return {'id': id}

	@reraise_as_400
	@return_code(200)
	def destroy(self, **kwargs):
		server = self._get_random_active_server()

		if server is None:
			raise Exception('No ACTIVE server found')

		server.delete()

		waiting_time = 0
		while waiting_time < self._TIMEOUT:
			time.sleep(self._POLL_TIME)
			waiting_time += 1
			try:
				self.nova.servers.get(id)
			except NotFound:
				# this means that the server is not found,
				# so it has been really deleted!
				break

		if waiting_time == self._TIMEOUT:
			raise Exception('timeout exceeded on delete')

		return {'id': id}

	@reraise_as_400
	@return_code(200)
	def snapshot(self):
		ans = {
			'cmps': {}
		}
		hosts = self.nova.hypervisors.list()
		# only active hosts
		hosts = filter(lambda h: h.vcpus_used != 0, hosts)

		#####
		# if you want to retrieve the host from the server:
		#
		# instance = api.nova.servers.list()[0]
		# hostname = getattr(instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname')
		# host = api.nova.hypervisors.find(hypervisor_hostname=hostname)
		#####

		for h in hosts:
			# cmps are always in the same order in the list.
			# we can use their index as a unique ID.
			host_index = self._known_cmps.index(h.host_ip)
			ans['cmps'][host_index] = {
				'hostname': h.hypervisor_hostname,
				'address': h.host_ip,
				'vcpus_used': h.vcpus_used,
				'memory_mb_used': h.memory_mb_used,
				'local_gb_used': h.local_gb_used,
				'r_vcpus': float(h.vcpus_used) / h.vcpus,
				'r_memory_mb': float(h.memory_mb_used) / h.memory_mb,
				'r_local_gb': float(h.local_gb_used) / h.local_gb
			}

		avg_r_vcpus = 0
		avg_r_memory_mb = 0
		avg_r_local_gb = 0

		n_active_hosts = float(len(hosts))

		if n_active_hosts > 0:
			avg_r_vcpus = sum([ans['cmps'][h]['r_vcpus'] for h in ans['cmps']]) / n_active_hosts
			avg_r_memory_mb = sum([ans['cmps'][h]['r_memory_mb'] for h in ans['cmps']]) / n_active_hosts
			avg_r_local_gb = sum([ans['cmps'][h]['r_local_gb'] for h in ans['cmps']]) / n_active_hosts

		ans['avg_r_vcpus'] = avg_r_vcpus
		ans['avg_r_memory_mb'] = avg_r_memory_mb
		ans['avg_r_local_gb'] = avg_r_local_gb
		ans['no_active_cmps'] = n_active_hosts

		return ans

	@reraise_as_400
	@return_code(200)
	def active_services(self):
		data = {}
		services = self.nova.services.list()
		names = [s.binary for s in services]
		unique_names = list(set(names))

		for i, name in enumerate(unique_names):
			data[i] = {
				'binary': name,
				'n': names.count(name)
			}

		return data