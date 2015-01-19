from bottle import route, run, request, response
from oslo.config import cfg
from oscard.sim import api
from oscard import exceptions
import urllib, urllib2

proxy_opts = [
	cfg.IntOpt(
		name='proxy_port',
		default=3000,
		help='Oscard proxy port'
	)
]

CONF = cfg.CONF
CONF.register_opts(proxy_opts)

nova_api = api.FakeAPI()

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

@route('/flavors', method='GET')
def flavors():
	body = nova_api.flavors
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
			url = url + '?' + params if params else url
			response = urllib2.urlopen(url)
		else:
			data = json.dumps(kwargs)
			req = urllib2.Request(url, data, headers={'Content-Type': 'application/json'})
			response = urllib2.urlopen(req)

		status = response.getcode()
		body = json.loads(response.read())
		if status == 400:
			# bad request
			raise exceptions.GenericException(body['msg'])
		return body

	def create(self, **kwargs):
		return self._send_request('create', method='POST', **kwargs)

	def resize(self, **kwargs):
		return self._send_request('resize', method='POST', **kwargs)

	def destroy(self, **kwargs):
		return self._send_request('destroy', method='POST', **kwargs)

	def flavors(self):
		return self._send_request('flavors')

if __name__ == '__main__':
	run(host='0.0.0.0', port=CONF.proxy_port)