from firebase import firebase
from oslo.config import cfg
import datetime

bifrost_opts = [
	cfg.StrOpt(
		name='fb_backend',
		default='https://fake.url.firebaseio.com',
		help='Bifrost app url on Firebase'
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
			self.app.put('/', 'last_sim_id', 0)

	def _seedpp(self):
		last_id = self.seed + 1
		self.app.put('/', 'last_sim_id', last_id)
		return last_id

	def add_snapshot(self, step, command_name, snapshot, sim_id=None):
		if not sim_id:
			sim_id = self.seed

		data = {
			'command': command_name,
			'hosts': snapshot
		}

		base_url = '/sims/' + str(sim_id) + '/snapshots'
		return self.app.put(base_url, str(step), data)

	def add_sim(self, steps, type, id=None, created_at=None):
		if not id:
			id = self._seedpp()

		if not created_at:
			created_at = str(datetime.datetime.now())

		data = {
			'steps': steps,
			'type': type,
			'created_at': created_at,
		}

		return self.app.put('/sims', str(id), data)