import logging

from spockbot.plugins.loader import PluginLoader as Client  # noqa

logger = logging.getLogger('spockbot')
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s]: %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)