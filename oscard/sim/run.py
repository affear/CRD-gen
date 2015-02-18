from oscard import config
config.init_conf()

from oslo.config import cfg
from oscard import log
from oscard.sim.proxy import ProxyAPI
from oscard.sim import collector
from oscard import randomizer
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
bifrost = collector.get_fb_backend()
random = randomizer.get_randomizer()

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
	saturation = {}
	prev_architecture = {}
	steps_run = {}

	for c in cmds_weighted:
		no_instr['no_' + c[0].name] = 0

	for i, p in enumerate(proxies):
		counts[i] = 0
		no_failures[i] = 0
		steps_run[i] = no_steps
		saturation[i] = False
		prev_architecture[i] = p.architecture()
		aggregates[i] = {
			'aggr_r_vcpus': 0,
			'aggr_r_memory_mb': 0,
			'aggr_r_local_gb': 0,
			'aggr_no_active_cmps': 0
		}

		hosts_dict[i] = {
			'services': p.services(),
			'address': p.host
		}

		# init every proxy
		try:
			resp = p.init()
		except Exception as e:
			LOG.error(e.message['msg'])
			return

		LOG.debug('Proxy inited with seed ' + str(resp['seed']))

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

	LOG.info('Simulation ID: ' + str(sim_id) + ', Steps: ' + str(no_steps))

	for t in xrange(no_steps):
		cmd = random.choice(cmds)
		for i, p in enumerate(proxies):
			# update architecture
			new_architecture = p.architecture()
			run_on_bifrost(bifrost.update_architecture, i, new_architecture)

			if len(new_architecture) > len(prev_architecture[i]):
				# this means that a node has been added.
				# so it means that the proxy is no more saturated!
				saturation[i] = False

			prev_architecture[i] = new_architecture
			if saturation[i]:
				# i-th proxy is saturated...
				# the simulation for him is over...
				LOG.warning(str(t) + ': proxy ' + str(p.host) + ' is saturated. No cmd will run on it.')
				steps_run[i] -= 1
				continue

			if counts[i] <= 0:  #there are no virtual machines... let's spawn one!
				cmd = CreateCommand()
			
			LOG.info(p.host + ': ' + str(t) + ' --> ' + cmd.name)
		
			counts[i], failure = cmd.execute(p, counts[i])

			# increment number of c/r/d
			no_instr['no_' + cmd.name] += 1

			snapshot = p.snapshot()
			if failure is not None:
				no_failures[i] += 1
				snapshot['failure'] = failure
				run_on_bifrost(bifrost.update_no_failures, i, no_failures[i])

				#TODO find a better way to do this...
				if 'No valid host' in failure['msg']:
					saturation[i] = True
				
			# create mapping between aggregates names
			# and snapshot names
			new_data = {
				'aggr_r_vcpus': snapshot['avg_r_vcpus'],
				'aggr_r_memory_mb': snapshot['avg_r_memory_mb'],
				'aggr_r_local_gb': snapshot['avg_r_local_gb'],
				'aggr_no_active_cmps': snapshot['no_active_cmps']
			}

			def update_aggr(key):
				old = aggregates[i][key]
				new = (old * t + new_data[key]) / float(t + 1)
				aggregates[i][key] = new

			update_aggr('aggr_r_vcpus')
			update_aggr('aggr_r_memory_mb')
			update_aggr('aggr_r_local_gb')
			update_aggr('aggr_no_active_cmps')

			# put aggregates into snapshot
			snapshot.update(aggregates[i])

			run_on_bifrost(bifrost.add_snapshot, i, t, cmd.name, snapshot)
			run_on_bifrost(bifrost.update_no_instr, no_instr)

	LOG.info(p.host + ': simulation ENDED')
	bifrost.add_end_to_current_sim(steps_run)

	import time
	for i, p in enumerate(proxies):
		# removing all remaining instances
		TIMEOUT = 10
		LOG.info(p.host + ': destroying all remaining instances in ' + str(TIMEOUT) + ' seconds')
		for t in xrange(1, TIMEOUT + 1):
			if t % 5 == 0:
				LOG.info(str(TIMEOUT - t) + ' seconds to destroy...')
			time.sleep(1)

		for times in xrange(counts[i]):
			DestroyCommand().execute(p, counts[i])