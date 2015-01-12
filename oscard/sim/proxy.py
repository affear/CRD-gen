from bottle import route, run, request, response
from oscard.sim import api
nova_api = api.FakeAPI()

@route('/create', method='POST')
def create():
	# TODO access data through `request.json`
	body, status = nova_api.create()
	response.status = status
	return body

@route('/resize', method='POST')
def resize():
	body, status = nova_api.resize()
	response.status = status
	return body

@route('/destroy', method='POST')
def destroy():
	body, status = nova_api.destroy()
	response.status = status
	return body

run(host="localhost", port=3000)