from oscard import config
config.init_conf()

from oslo.config import cfg
import random
from oscard import log
from oscard.sim.proxy import ProxyAPI
from oscard.sim.collector import BifrostAPI
import webbrowser

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
bifrost = BifrostAPI()

# Virtual classes for commands
class BaseCommand(object):
	'''
		The abstract command interface
	'''
	name = 'base_command'

	def execute(self, proxy, count):
		# invoke nova apis
		# use context
		# return new context
		raise NotImplementedError

	class Meta:
		abstract = True

class CreateCommand(BaseCommand):
	name = 'create'

	def execute(self, proxy, count):
		failure = None
		try:
			resp = proxy.create()
			count += 1

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(str(e.message))
			failure = e.message
		finally:
			return count, failure

class DestroyCommand(BaseCommand):
	name = 'destroy'

	def execute(self, proxy, count):
		failure = None
		try:
			resp = proxy.destroy()
			count -= 1

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(str(e.message))
			failure = e.message
		finally:
			return count, failure

class ResizeCommand(BaseCommand):
	name = 'resize'

	def execute(self, proxy, count):
		failure = None
		try:
			resp = proxy.resize()

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(str(e.message))
			failure = e.message
		finally:
			return count, failure

def main():
	celery_ok = True

	# checking if Celery is up
	from celery.task.control import inspect
	try:
		if not inspect().stats():
			celery_ok = False
			LOG.warning('No celery worker is up. NOT using Celery')
	except:
		celery_ok = False
		LOG.warning('RabbitMQ refused connection. NOT using Celery')

	def run_on_bifrost(method, *args):
		if celery_ok:
			method.delay(*args)
		else:
			method(*args)

	no_steps = CONF.sim.no_t

	# weights for commands
	C_WEIGHT = 6
	R_WEIGHT = 2
	D_WEIGHT = 2
	assert C_WEIGHT + R_WEIGHT + D_WEIGHT == 10

	cmds_weighted = [
		(CreateCommand(), C_WEIGHT),
		(ResizeCommand(), R_WEIGHT),
		(DestroyCommand(), D_WEIGHT),
	]
	cmds = [val for val, cnt in cmds_weighted for i in range(cnt)]

	counts = {}
	hosts_dict = {}
	no_instr = {}
	no_failures = {}
	aggregates = {}
	for c in cmds_weighted:
		no_instr['no_' + c[0].name] = 0

	for p in proxies:
		counts[p.host] = 0
		no_failures[p.host] = 0
		aggregates[p.host] = {
			'agg_r_vcpus': 0,
			'agg_r_memory_mb': 0,
			'agg_r_local_gb': 0
		}

		sim_type = 'smart' if p.is_smart()['smart'] else 'normal'
		hosts_dict[p.host] = sim_type

	sim_id, _ = bifrost.add_sim(no_steps, hosts_dict)

	# open tab in chrome
	try:
		import webbrowser
		import os
		chrome = webbrowser.get('google-chrome')
		url = os.path.join(CONF.fb_backend, 'sims', str(sim_id))
		chrome.open_new_tab(url)
		LOG.info('Tab opened in Chrome at ' + url)
	except:
		LOG.warning('Cannot open sim tab in Chrome')

	LOG.info('Simulation ID: ' + str(sim_id))

	for t in xrange(no_steps):
		cmd = {}
		for p in proxies:
			if counts[p.host] > 0:
				cmd[p.host] = random.choice(cmds)
			else: #there are no virtual machines... let's spawn one!
				cmd[p.host] = CreateCommand()
			
			LOG.info(p.host + ': ' + str(t) + ' --> ' + cmd[p.host].name)
		
			counts[p.host], failure = cmd[p.host].execute(p, counts[p.host])

			# increment number of c/r/d
			no_instr['no_' + cmd[p.host].name] += 1

			snapshot = None
			if failure is not None:
				no_failures[p.host] += 1
				snapshot = {'failure': failure}
				run_on_bifrost(bifrost.add_failure, p.host, t, failure)
				run_on_bifrost(bifrost.update_no_failures, p.host, no_failures[p.host])
			else:
				snapshot = p.snapshot()

				# update aggregates
				avg_r_vcpus = snapshot['avg_r_vcpus']
				avg_r_memory_mb = snapshot['avg_r_memory_mb']
				avg_r_local_gb = snapshot['avg_r_local_gb']

				# vcpu
				old_r_vcpu = aggregates[p.host]['agg_r_vcpus']
				new_r_vcpu = (old_r_vcpu * t + avg_r_vcpus) / float(t + 1)
				aggregates[p.host]['agg_r_vcpus'] = new_r_vcpu

				# ram
				old_r_ram = aggregates[p.host]['agg_r_memory_mb']
				new_r_ram = (old_r_ram * t + avg_r_memory_mb) / float(t + 1)
				aggregates[p.host]['agg_r_memory_mb'] = new_r_ram

				# disk
				old_r_disk = aggregates[p.host]['agg_r_local_gb']
				new_r_disk = (old_r_disk * t + avg_r_local_gb) / float(t + 1)
				aggregates[p.host]['agg_r_local_gb'] = new_r_disk


			run_on_bifrost(bifrost.add_snapshot, p.host, t, cmd[p.host].name, snapshot)
			run_on_bifrost(bifrost.update_no_instr, no_instr)
			run_on_bifrost(bifrost.update_aggregates, p.host, aggregates[p.host])

	LOG.info(p.host + ': simulation ENDED')
	bifrost.add_end_to_current_sim()

	import time
	for p in proxies:
		# removing all remaining instances
		TIMEOUT = 30
		LOG.info(p.host + ': destroying all remaining instances in ' + str(TIMEOUT) + ' seconds')
		for t in xrange(1, TIMEOUT + 1):
			if t % 5 == 0:
				LOG.info(str(TIMEOUT - t) + ' seconds to destroy...')
			time.sleep(1)

		for times in xrange(counts[p.host]):
			DestroyCommand().execute(p, counts[p.host])