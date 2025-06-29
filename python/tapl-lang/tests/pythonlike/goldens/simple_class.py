from tapl_lang.pythonlike.predef import *

class SimplestClass:
    pass

def accept(param):
    pass
accept(SimplestClass())

class Device:
    def get_firmware_version(self):
        return 'v42'

def process_device(device):
    print__tapl(device.get_firmware_version())

process_device(Device())
