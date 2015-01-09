# The OpenStack Way
from oslo.config import cfg
DEFAULT_CONFIG_FILE = 'oscard.conf'
CONF = cfg.CONF

def load_conf_file():
	CONF(default_config_files=[DEFAULT_CONFIG_FILE, ])

def init_conf(): # in OpenStack, it is parse_args()
	load_conf_file()