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
		default='0.0.0.0',
		help='Oscard proxy host'
	),
	cfg.StrOpt(
		name='ctrl_host',
		default='localhost',
		help='OpenStack controller host'
	),
	cfg.IntOpt(
		name='glance_port',
		default=9292,
		help='Glance port'
	),
	cfg.IntOpt(
		name='keystone_port',
		default=35357,
		help='Keystone port'
	),
	cfg.IntOpt(
		name='nova-api_port',
		default=8773,
		help='Nova API port'
	),
	cfg.StrOpt(
		name='os_username',
		default='admin',
		help='OpenStack username (make it match OS conf)'
	),
	cfg.StrOpt(
		name='os_tenant',
		default='admin',
		help='OpenStack tenant name (make it match OS conf)'
	),
	cfg.StrOpt(
		name='os_password',
		default='pwstack',
		help='OpenStack password (make it match OS conf)'
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

from keystoneclient.v2_0 import client as ksclient
from novaclient.v1_1 import client as nvclient
from glanceclient.v2 import client as glclient
class NovaAPI(CRDAPI):
	_baseurl = 'http://' + CONF.ctrl_host

	def __init__(self):
		self.creds = {}
		self.creds['auth_url'] = self._baseurl + ':' + str(CONF.keystone_port) + '/v2.0'
		self.creds['username'] = CONF.os_username
		self.creds['password'] = CONF.os_password
		self.creds['tenant_name'] = CONF.os_tenant

		self.keystone = ksclient.Client(**self.creds)
		self.nova = nvclient.Client(**self.creds)
		glance_endpoint = keystone.service_catalog.url_for(service_type='image', endpoint_type='publicURL')
		self.glance = glclient.Client(glance_endpoint, token=keystone.auth_token)

		self.default_image = glance.images.list().next() # ['name']