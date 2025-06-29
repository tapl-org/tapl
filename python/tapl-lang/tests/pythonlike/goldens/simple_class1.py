from tapl_lang.pythonlike import predef1 as predef
s0 = predef.Scope(predef.predef_scope)

class SimplestClass:
    pass
s0.SimplestClass = predef.Scope(parent=None, __call__=predef.init_class)

def accept(param):
    s1 = predef.Scope(s0, param=param)
    pass
    return predef.get_return_type(s1)
s0.accept = predef.FunctionType([s0.SimplestClass], accept(s0.SimplestClass))
s0.accept(s0.SimplestClass.new())

class Device:
    def get_firmware_version(self):
        s1 = predef.Scope(s0, self=self)
        predef.add_return_type(s1, s1.Str)
        return predef.get_return_type(s1)

s0.Device = predef.Scope(parent=None, __call__=predef.init_class)
s0.Device.get_firmware_version = predef.FunctionType([], Device.get_firmware_version(s0.Device))

def process_device(device: s0.Device):
    s1 = predef.Scope(s0, device=device)
    s1.print__tapl(s1.device.get_firmware_version())
    return predef.get_return_type(s1)

s0.process_device = predef.FunctionType([s0.Device], process_device(s0.Device))
s0.process_device(s0.Device())
