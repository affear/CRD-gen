from oslo.config import cfg
import random

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

from oscard.sim import api as nova_api
api = nova_api.NovaAPI()

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
		api.create()
		ctxt['vms'].append(ctxt['vm_id'] + 1)
		return ctxt

class DestroyCommand(BaseCommand):
	name = 'destroy'

	def execute(self, ctxt):
		vm_id = random.choice(ctxt['vms'])
		api.destroy()
		ctxt['vms'].remove(vm_id)
		return ctxt

class ResizeCommand(BaseCommand):
	name = 'resize'

	def execute(self, ctxt):
		api.resize()
		return ctxt

def main():
	from oscard import config
	config.init_conf()
	
	cmds = [
		CreateCommand,
		ResizeCommand,
		DestroyCommand,
	]

	ctxt = {
		'vm_id': 0,
		'vms': []
	}

	for t in xrange(CONF.sim.no_t):
		if len(ctxt['vms']) > 0:
			ctxt = random.choice(cmds)().execute(ctxt)
		else: #there are no virtual machines... let's spawn one!
			ctxt = cmds[0]().execute(ctxt)
	