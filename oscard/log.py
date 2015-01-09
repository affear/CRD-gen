from oslo.config import cfg
import logging

log_group = cfg.OptGroup(name='logs')
log_opts = [
	cfg.StrOpt(
		'sim_log_file',
		default= 'logs/sim.log',
		help='Simulation log file'
	),
]
CONF = cfg.CONF
CONF.register_group(log_group)
CONF.register_opts(log_opts, log_group)

_loggers = {}

def get_logger(name,
		file_name=None,
		formatting='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):

	if name in _loggers:
		return _loggers[name]

	if not file_name:
		file_name = 'logs/' + str(name) + '.log'

	logger = logging.getLogger(name)
	formatter = logging.Formatter(formatting)
	fileHandler = logging.FileHandler(file_name, mode='w')
	fileHandler.setFormatter(formatter)
	streamHandler = logging.StreamHandler()
	streamHandler.setFormatter(formatter)

	logger.setLevel(logging.DEBUG)
	logger.addHandler(fileHandler)
	logger.addHandler(streamHandler)
	_loggers[name] = logger
	return logger