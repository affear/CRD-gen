from firebase import firebase
from oslo.config import cfg

bifrost_opts = [
	cfg.StrOpt(
		name='bifrost_fb_url',
		default='http://bifrosturl.fake.firebase.com',
		help='Bifrost app url on Firebase'
	)
]

CONF = cfg.CONF
CONF.register_opts(bifrost_opts)

class BifrostAPI(object):
	app = firebase.FirebaseApplication(CONF.bifrost_fb_url, None)

	@property
	def seed(self):
		pass

	def seedpp(self):
		pass

	def add_snapshot(self, seed, snapshot):
		pass

	def add_sim(self, seed):
		pass