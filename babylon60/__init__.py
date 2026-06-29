import sys
import types
import importlib.abc
import importlib.util
import os
import threading

if not hasattr(sys, '_cortex_babylon_local'):
    sys._cortex_babylon_local = threading.local()

class ProxyModule(types.ModuleType):
    def __init__(self, name, real_module):
        super().__init__(name)
        object.__setattr__(self, '_real_module', real_module)

    def __getattribute__(self, name):
        if name in ('_real_module', '__class__', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            return object.__getattribute__(self, name)
        
        # Check if the attribute is a bound submodule on this proxy module
        try:
            val = object.__getattribute__(self, name)
            if isinstance(val, types.ModuleType):
                return val
        except AttributeError:
            pass

        if name == '__dict__':
            try:
                real = object.__getattribute__(self, '_real_module')
            except AttributeError:
                return object.__getattribute__(self, '__dict__')
            d = dict(real.__dict__)
            d.update({
                '__name__': object.__getattribute__(self, '__name__'),
            })
            try:
                d['__spec__'] = object.__getattribute__(self, '__spec__')
            except AttributeError:
                pass
            try:
                d['__loader__'] = object.__getattribute__(self, '__loader__')
            except AttributeError:
                pass
            if hasattr(self, '__path__'):
                d['__path__'] = object.__getattribute__(self, '__path__')
            if hasattr(self, '__file__'):
                d['__file__'] = object.__getattribute__(self, '__file__')
            return d

        return getattr(self._real_module, name)

    def __setattr__(self, name, value):
        if name in ('_real_module', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            object.__setattr__(self, name, value)
        elif isinstance(value, types.ModuleType):
            object.__setattr__(self, name, value)
        else:
            setattr(self._real_module, name, value)

    def __dir__(self):
        return dir(self._real_module)


class LazyAliasLoader(importlib.abc.Loader):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name

    def create_module(self, spec):
        real_module_name = spec.name.replace(self.alias_name, self.real_name, 1)
        real_module = importlib.import_module(real_module_name)
        
        proxy = ProxyModule(spec.name, real_module)
        if hasattr(real_module, '__path__'):
            proxy.__path__ = real_module.__path__
        if hasattr(real_module, '__file__'):
            proxy.__file__ = real_module.__file__
            
        return proxy

    def exec_module(self, module):
        pass


class AliasFinder(importlib.abc.MetaPathFinder):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name

    def _has_physical_module(self, fullname):
        parts = fullname.split('.')
        if parts[0] != self.alias_name:
            return False
        rel_path = os.path.join(*parts[1:]) if len(parts) > 1 else ''
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_py = os.path.join(base_dir, rel_path + '.py')
        target_dir = os.path.join(base_dir, rel_path)
        
        return os.path.isfile(target_py) or os.path.isdir(target_dir)

    def find_spec(self, fullname, path, target=None):
        if getattr(sys._cortex_babylon_local, 'guard', False):
            return None

        if fullname == self.alias_name or fullname.startswith(self.alias_name + '.'):
            if self._has_physical_module(fullname):
                return None
                
            real_name = fullname.replace(self.alias_name, self.real_name, 1)
            
            sys._cortex_babylon_local.guard = True
            try:
                spec = importlib.util.find_spec(real_name)
                if spec is None:
                    return None
            except Exception:
                return None
            finally:
                sys._cortex_babylon_local.guard = False

            return importlib.util.spec_from_loader(
                fullname,
                LazyAliasLoader(self.alias_name, self.real_name)
            )
        return None


# Install the proxy in sys.meta_path so that all submodules of babylon60
# resolve to cortex's submodules without executing code twice.
# We ensure it's not added multiple times if reloaded.
if not any(isinstance(f, AliasFinder) and f.alias_name == 'babylon60' for f in sys.meta_path):
    sys.meta_path.insert(0, AliasFinder('babylon60', 'cortex'))

# Create the root proxy module and register it in sys.modules
import cortex
babylon_root = ProxyModule('babylon60', cortex)
babylon_root.__path__ = [os.path.dirname(os.path.abspath(__file__))]
if hasattr(cortex, '__file__'):
    babylon_root.__file__ = cortex.__file__

sys.modules['babylon60'] = babylon_root
