from oslo.config import cfg
from oscard import config
from oscard.sim import collector
import random

bifrost = collector.get_fb_backend()

random_opts = [
	cfg.IntOpt(
		name='random_seed',
		default=0,
		help='All random generators seed'
	)
]

CONF = cfg.CONF
CONF.register_opts(random_opts)

def get_seed():
	config.reload_conf(CONF)
	seed = CONF.random_seed - 1
	# -1 because simulation N
	# will be run with seed N -1
	return seed if seed >= 0 else bifrost.seed

def get_randomizer():
	seed = get_seed()
	r = random.Random()
	r.seed(seed)
	return r