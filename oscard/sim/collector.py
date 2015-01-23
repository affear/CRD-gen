from firebase import firebase
from oslo.config import cfg
import datetime

bifrost_opts = [
	cfg.StrOpt(
		name='fb_backend',
		default='https://fake.url.firebaseio.com',
		help='Your app url on Firebase'
	)
]

CONF = cfg.CONF
CONF.register_opts(bifrost_opts)

class BifrostAPI(object):
	app = firebase.FirebaseApplication(CONF.fb_backend, None)

	@property
	def seed(self):
		return self.app.get('/last_sim_id', None)

	def __init__(self):
		if not self.seed:
			self.app.put('/', 'last_sim_id', -1)

	def _seedpp(self):
		last_id = self.seed + 1
		self.app.put('/', 'last_sim_id', last_id)
		return last_id

	def add_snapshot(self, host, step, command_name, snapshot, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		snapshot['command'] = command_name

		base_url = '/sims/' + str(sim_id) + '/' + str(host) + '/snapshots'
		return self.app.put(base_url, str(step), snapshot)

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
		'''
		if not id:
			id = self._seedpp()

		if not created_at:
			created_at = str(datetime.datetime.now())

		data = {
			'steps': steps,
			'created_at': created_at,
		}

		for h in hosts_dict:
			data[h] = {'type': hosts_dict[h]}

		return self.app.put('/sims', str(id), data)