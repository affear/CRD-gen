from oscard import config
config.init_conf()

from bottle import route, run, request, response
from oslo.config import cfg
from oscard import log
from oscard.sim import api, collector
import urllib, urllib2

proxy_opts = [
	cfg.IntOpt(
		name='proxy_port',
		default=3000,
		help='Oscard proxy port'
	),
	cfg.BoolOpt(
		name='fake',
		default=True,
		help='Fake simulation or not?'
	)
]

CONF = cfg.CONF
CONF.register_opts(proxy_opts)
LOG = log.get_logger(__name__)

nova_api = None
if CONF.fake:
	LOG.info('using FakeAPI')
	nova_api = api.FakeAPI()
else:
	LOG.info('using NovaAPI')
	nova_api = api.NovaAPI()

@route('/create', method='POST')
def create():
	body, status = nova_api.create(**request.json)
	response.status = status
	return body

@route('/resize', method='POST')
def resize():
	body, status = nova_api.resize(**request.json)
	response.status = status
	return body

@route('/destroy', method='POST')
def destroy():
	body, status = nova_api.destroy(**request.json)
	response.status = status
	return body

@route('/snapshot', method='GET')
def snapshot():
	body, status = nova_api.snapshot()
	response.status = status
	return body

@route('/smart', method='GET')
def smart():
	body, status = nova_api.is_smart()
	response.status = status
	return body

bifrost = collector.get_fb_backend()
@route('/seed', method='GET')
def seed():
	body = {'seed': bifrost.seed}
	response.status = 200
	return body

@route('/arch', method='GET')
def architecture():
	body, status = nova_api.architecture
	response.status = 200
	return body

class ProxyAPI(api.CRDAPI):
	'''
		The API to access the proxy
	'''

	def __init__(self, host):
		self.host = host
		self._baseurl = 'http://' + host

	def _send_request(self, endpoint='', method='GET', **kwargs):
		import json, os
		url = os.path.join(self._baseurl, endpoint)

		if method == 'GET':
			params = urllib.urlencode(kwargs)
			req = url + '?' + params if params else url
		else:
			data = json.dumps(kwargs)
			req = urllib2.Request(url, data, headers={'Content-Type': 'application/json'})

		try:
			response = urllib2.urlopen(req)
			body = json.loads(response.read())
		except urllib2.HTTPError as e:
			body = json.loads(e.read())
			raise Exception(body)
		
		return body

	def create(self, **kwargs):
		return self._send_request('create', method='POST', **kwargs)

	def resize(self, **kwargs):
		return self._send_request('resize', method='POST', **kwargs)

	def destroy(self, **kwargs):
		return self._send_request('destroy', method='POST', **kwargs)

	def snapshot(self):
		return self._send_request('snapshot', method='GET')

	def is_smart(self):
		return self._send_request('smart', method='GET')

	def seed(self):
		return self._send_request('seed', method='GET')

	def architecture(self):
		return self._send_request('arch', method='GET')

if __name__ == '__main__':
	run(host='0.0.0.0', port=CONF.proxy_port)