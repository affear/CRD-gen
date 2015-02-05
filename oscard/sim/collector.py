from firebase import firebase
from celery.contrib.methods import task
from celery import Celery
from oslo.config import cfg
import datetime
from oscard import config, log

bifrost_opts = [
	cfg.StrOpt(
		name='fb_backend',
		default='https://fake.url.firebaseio.com',
		help='Your app url on Firebase'
	)
]

CONF = cfg.CONF
CONF.register_opts(bifrost_opts)
LOG = log.get_logger(__name__)

cel = Celery('bifrost_tasks', backend='amqp', broker='amqp://guest@localhost//')

class FakeFirebaseApplication(object):
	'''
		Class that mimics Firebase in a fake context.
		It will be used once results cannot be stored online.
	'''
	id = 0

	def put(self, *args, **kwargs):
		return {}

	def patch(self, *args, **kwargs):
		return {}

	def get(self, *args, **kwargs):
		if args[0] == '/last_sim_id':
			return self.id

		if args[0] == '/sims/' + str(self.id) and args[1] == 'start':
			return str(datetime.datetime.now())

class BifrostAPI(object):

	@property
	def seed(self):
		return self.app.get('/last_sim_id', None)

	def __init__(self):
		# we have to init from configuration file
		# in case the module is run from celery worker!
		# we do it inside __init__ because of conflicts
		# between oslo and celery worker...
		config.init_conf()
		LOG.info('Connecting to firebase backend (' + CONF.fb_backend + ')...')
		self.app = firebase.FirebaseApplication(CONF.fb_backend, None)

		try:
			# doing a get request to test connection
			self.seed
		except Exception as e:
			self.app = FakeFirebaseApplication()
			LOG.warning('No Firebase backend created! Results will NOT be stored.')

		if self.seed is None:
			self.app.put('/', 'last_sim_id', -1)

	def _seedpp(self):
		last_id = self.seed + 1
		self.app.put('/', 'last_sim_id', last_id)
		return last_id

	@task(name='bifrost.update_architecture')
	def update_architecture(self, host_id, arch, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		base_url = '/sims/' + str(sim_id) + '/proxies/' + str(host_id)

		return self.app.put(base_url, 'architecture', arch)

	@task(name='bifrost.update_no_failures')
	def update_no_failures(self, host_id, nf, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		base_url = '/sims/' + str(sim_id) + '/proxies/' + str(host_id)

		return self.app.put(base_url, 'no_failures', nf)

	@task(name='bifrost.add_snapshot')
	def add_snapshot(self, host_id, step, command_name, snapshot, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		snapshot['command'] = command_name
		base_url = '/sims/' + str(sim_id) + '/proxies/' + str(host_id)

		return self.app.put(base_url + '/snapshots', str(step), snapshot)

	@task(name='bifrost.update_no_instr')
	def update_no_instr(self, no_instr, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		return self.app.patch('/sims/' + str(sim_id), no_instr)

	def add_sim(self, steps, hosts_dict, id=None, created_at=None):
		'''
			- steps: the number of steps
			- hosts_dict: a dict with host_id as key and simulation
				type and host address as value. For instance:
					{
						1: {
							'type': 'normal',
							'address': '192.168.0.1:7000'
						},
						2: {
							'type': 'smart',
							'address': '10.169.4.2:3000'
						}
					}
			- id: the simulation id
			- created_at: creation time

			Not a task. We need sync on id++.
		'''
		if not id:
			id = self._seedpp()

		if not created_at:
			created_at = str(datetime.datetime.now())

		for h in hosts_dict:
				hosts_dict[h]['no_failures'] = 0

		data = {
			'proxies': hosts_dict,
			'steps': steps,
			'start': created_at,
		}

		self.app.patch('/', {'running': True})
		return id, self.app.put('/sims', str(id), data)

	def add_end_to_current_sim(self, steps_run):
		default_formatting = '%Y-%m-%d %H:%M:%S.%f'
		id = self.seed

		start = self.app.get('/sims/' + str(id), 'start')
		start = datetime.datetime.strptime(start, default_formatting)
		end = datetime.datetime.now()

		delta = abs(end - start)
		minutes = delta.seconds / 60
		seconds = delta.seconds % 60

		elapsed_time = str(minutes) + 'm:' + str(seconds) + 's'

		data = {
			'end': str(end),
			'elapsed_time': elapsed_time,
		}

		self.app.patch('/', {'running': False})

		# add steps run to each proxy
		for p_id in steps_run:
			url = '/sims/' + str(id) + '/proxies/' + str(p_id)
			self.app.patch(url, {'steps_run': steps_run[p_id]})

		return self.app.patch('/sims/' + str(id), data)