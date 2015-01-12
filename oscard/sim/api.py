import urllib, urllib2
from oslo.config import cfg
from oscard import log

oscard_opts = [
	cfg.IntOpt(
		name='proxy_port',
		default=3000,
		help='Oscard proxy port'
	),
	cfg.StrOpt(
		name='proxy_host',
		default='localhost',
		help='Oscard proxy host'
	),
]

CONF = cfg.CONF
CONF.register_opts(oscard_opts)
LOG = log.get_logger(__name__)

class CRDAPI(object):
	_baseurl = 'http://localhost'

	def create(self, **kwargs):
		raise NotImplementedError

	def resize(self, **kwargs):
		raise NotImplementedError

	def destroy(self, **kwargs):
		raise NotImplementedError

class FakeAPI(CRDAPI):

	def create(self, **kwargs):
		LOG.info("novapi: create")
		return {"body": "created"}, 200

	def resize(self, **kwargs):
		LOG.info("novapi: resize")
		return {"body": "resized"}, 200

	def destroy(self, **kwargs):
		LOG.info("novapi: destroy")
		return {"body": "destroyed"}, 200

class NovaAPI(CRDAPI):
	_baseurl = ''

	pass

class OscardAPI(CRDAPI):

	# this should be the proxy url
	_baseurl = 'http://' + CONF.proxy_host + ':' + str(CONF.proxy_port)

	def _send_request(self, endpoint='', **kwargs):
		import json, os
		url = os.path.join(self._baseurl, endpoint)
		data = urllib.urlencode(kwargs)
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		return json.loads(response.read())

	def create(self, **kwargs):
		return self._send_request('create', **kwargs)

	def resize(self, **kwargs):
		return self._send_request('resize', **kwargs)

	def destroy(self, **kwargs):
		return self._send_request('destroy', **kwargs)