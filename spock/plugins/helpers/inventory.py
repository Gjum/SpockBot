"""
Inventory plugin is a helper plugin for dealing with interaction with inventories
"""

from spock.utils import pl_announce
from spock.mcp import mcdata, mcpacket

class InventoryCore:
	def __init__(self, clinfo, net):
		self.clinfo = clinfo
		self.net = net
	
	def test_inventory(self):
		data = {
			'window_id': 0,
			'slot': 36,
			'button': 0,
			'mode': 0,
			'action': 1,
			'clicked_item': self.clinfo.inventory.slots[36], 
		}
		self.net.push_packet(
			'PLAY>Click Window', data
		)
		data = {
			'window_id': 0,
			'slot': 37,
			'button': 0,
			'mode': 0,
			'action': 1,
			'clicked_item': self.clinfo.inventory.slots[37], 
		}
		self.net.push_packet(
			'PLAY>Click Window', data
		)

@pl_announce('Inventory')
class InventoryPlugin:
	def __init__(self, ploader, settings):
		self.clinfo = ploader.requires('ClientInfo')
		self.net = ploader.requires('Net')
		self.inventory = InventoryCore(self.clinfo, self.net)
		ploader.provides('Inventory', self.inventory)
	
