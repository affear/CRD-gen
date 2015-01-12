import urllib, urllib2
from oscard import log

LOG = log.get_logger(__name__)

class FakeAPI(object):

	def create(self, **kwargs):
		LOG.info("novapi: create")
		return {"body": "created"}, 200

	def resize(self, **kwargs):
		LOG.info("novapi: resize")
		return {"body": "resized"}, 200

	def destroy(self, **kwargs):
		LOG.info("novapi: destroy")
		return {"body": "destroyed"}, 200

class NovaAPI(object):
	_baseurl = ''

	pass