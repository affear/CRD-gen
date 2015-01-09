import urllib, urllib2
from oscard import log

LOG = log.get_logger(__name__)

class NovaAPI(object):
	_baseurl = ''

	def create(self, **kwargs):
		LOG.info("novapi: create")
		return {"response": "OK", "status": "200"}

	def resize(self, **kwargs):
		LOG.info("novapi: resize")
		return {"response": "OK", "status": "200"}

	def destroy(self, **kwargs):
		LOG.info("novapi: destroy")
		return {"response": "OK", "status": "200"}