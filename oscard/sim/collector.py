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
		self.app = firebase.FirebaseApplication(CONF.fb_backend, None)

		if self.seed is None:
			self.app.put('/', 'last_sim_id', -1)

	def _seedpp(self):
		last_id = self.seed + 1
		self.app.put('/', 'last_sim_id', last_id)
		return last_id

	def _parse_host(self, host_ip_port):
		return host_ip_port.replace('.', '_').replace(':', '__')

	@task(name='bifrost.add_failure')
	def add_failure(self, host, step, f, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		host = self._parse_host(host)
		base_url = '/sims/' + str(sim_id) + '/' + str(host)

		return self.app.put(base_url + '/failures', str(step), f)

	@task(name='bifrost.update_no_failures')
	def update_no_failures(self, host, nf, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		host = self._parse_host(host)
		base_url = '/sims/' + str(sim_id) + '/' + str(host)

		return self.app.put(base_url, 'no_failures', nf)

	@task(name='bifrost.add_snapshot')
	def add_snapshot(self, host, step, command_name, snapshot, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		host = self._parse_host(host)
		snapshot['command'] = command_name
		base_url = '/sims/' + str(sim_id) + '/' + str(host)

		return self.app.put(base_url + '/snapshots', str(step), snapshot)

	@task(name='bifrost.update_no_instr')
	def update_no_instr(self, no_instr, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		return self.app.patch('/sims/' + str(sim_id), no_instr)

	@task(name='bifrost.update_aggregates')
	def update_aggregates(self, host, aggr, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		host = self._parse_host(host)
		print aggr
		print host
		base_url = '/sims/' + str(sim_id) + '/' + str(host)

		return self.app.patch(base_url, aggr)

	def add_sim(self, steps, hosts_dict, id=None, created_at=None):
		'''
			- steps: the number of steps
			- hosts_dict: a dict with hostname as key and simulation
				type as value. For instance:
					{
						'host1': 'normal',
						'host2': 'smart',
					}
			- id: the simulation id
			- created_at: creation time

			Not a task. We need sync on id++.
		'''
		if not id:
			id = self._seedpp()

		if not created_at:
			created_at = str(datetime.datetime.now())

		data = {
			'steps': steps,
			'start': created_at,
		}

		for h in hosts_dict:
			data[self._parse_host(h)] = {
				'type': hosts_dict[h],
				'no_failures': 0
			}

		return id, self.app.put('/sims', str(id), data)

	def add_end_to_current_sim(self):
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
			'elapsed_time': elapsed_time
		}
		return self.app.patch('/sims/' + str(id), data)