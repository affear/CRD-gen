# The OpenStack Way
from oslo.config import cfg
DEFAULT_CONFIG_FILE = 'oscard.conf'
CONF = cfg.CONF	

def init_conf():
	CONF(default_config_files=[DEFAULT_CONFIG_FILE, ])

def reload_conf(conf):
	conf.reload_config_files()