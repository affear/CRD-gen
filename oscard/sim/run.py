from oslo.config import cfg
import random
from oscard import exceptions, log
from oscard.sim.proxy import ProxyAPI

sim_group = cfg.OptGroup(name='sim')
sim_opts = [
	cfg.IntOpt(
		name='no_t',
		default=10,
		help='The number of steps of the simulation'
	),
]

CONF = cfg.CONF
CONF.register_group(sim_group)
CONF.register_opts(sim_opts, sim_group)
LOG = log.get_logger(__name__)

api = ProxyAPI()
FLAVORS = api.flavors()

# Virtual classes for commands
class BaseCommand(object):
	'''
		The abstract command interface
	'''
	name = 'base_command'

	def execute(self, ctxt):
		# invoke nova apis
		# use context
		# return new context
		return {}

	class Meta:
		abstract = True

class CreateCommand(BaseCommand):
	name = 'create'

	def execute(self, ctxt):
		kwargs = {
			'flavor': FLAVORS[random.choice(FLAVORS.keys())],
		}

		try:
			ans = api.create(**kwargs)
			ctxt.append(ans['id'])
		except exceptions.GenericException as e:
			LOG.error(e.message)
		finally:
			return ctxt

class DestroyCommand(BaseCommand):
	name = 'destroy'

	def execute(self, ctxt):
		id = random.choice(ctxt)
		try:
			api.destroy()
			ctxt.remove(id)
		except exceptions.GenericException as e:
			LOG.error(e.message)
		finally:
			return ctxt

class ResizeCommand(BaseCommand):
	name = 'resize'

	def execute(self, ctxt):
		kwargs = {
			'id': random.choice(ctxt),
			'flavor': FLAVORS[random.choice(FLAVORS.keys())]
		}

		try:
			api.resize(**kwargs)
		except exceptions.GenericException as e:
			LOG.error(e.message)
		finally:
			return ctxt

def main():
	from oscard import config, log
	config.init_conf()
	
	LOG = log.get_logger(__name__)

	cmds = [
		CreateCommand,
		ResizeCommand,
		DestroyCommand,
	]

	IDS = []

	for t in xrange(CONF.sim.no_t):
		if len(IDS) > 0:
			cmd = random.choice(cmds)()
		else: #there are no virtual machines... let's spawn one!
			cmd = CreateCommand()
			
		LOG.info(str(t) + ' --> ' + cmd.name)
		IDS = cmd.execute(IDS)