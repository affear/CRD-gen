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
	cfg.ListOpt(
		name='proxy_hosts',
		default=['0.0.0.0:3000', ],
		help='Oscard proxy host'
	)
]

CONF = cfg.CONF
CONF.register_group(sim_group)
CONF.register_opts(sim_opts, sim_group)
LOG = log.get_logger(__name__)

proxies = [ProxyAPI(host) for host in CONF.sim.proxy_hosts]
FLAVOR_IDS = xrange(1, 6) 

# Virtual classes for commands
class BaseCommand(object):
	'''
		The abstract command interface
	'''
	name = 'base_command'

	def execute(self, proxy, ctxt):
		# invoke nova apis
		# use context
		# return new context
		return {}

	class Meta:
		abstract = True

class CreateCommand(BaseCommand):
	name = 'create'

	def execute(self, proxy, ctxt):
		kwargs = {
			'flavor_id': random.choice(FLAVOR_IDS),
		}

		try:
			ans = proxy.create(**kwargs)
			ctxt.append(ans['id'])
		except exceptions.GenericException as e:
			LOG.error(e.message)
		finally:
			return ctxt

class DestroyCommand(BaseCommand):
	name = 'destroy'

	def execute(self, proxy, ctxt):
		kwargs = {
			'id': random.choice(ctxt)
		}
		try:
			proxy.destroy(**kwargs)
			ctxt.remove(id)
		except exceptions.GenericException as e:
			LOG.error(e.message)
		finally:
			return ctxt

class ResizeCommand(BaseCommand):
	name = 'resize'

	def execute(self, proxy, ctxt):
		kwargs = {
			'id': random.choice(ctxt),
			'flavor_id': random.choice(FLAVOR_IDS)
		}

		try:
			proxy.resize(**kwargs)
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

	ctxts = {}
	for p in proxies:
		ctxts[p.host] = []

	for p in proxies:
		for t in xrange(CONF.sim.no_t):
			if len(ctxts[p.host]) > 0:
				cmd = random.choice(cmds)()
			else: #there are no virtual machines... let's spawn one!
				cmd = CreateCommand()
				
			LOG.info(p.host + ': ' + str(t) + ' --> ' + cmd.name)
			
			ctxts[p.host] = cmd.execute(p, ctxts[p.host])