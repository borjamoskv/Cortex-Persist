import importlib.abc
import importlib.util
import os
import sys
import threading
import types

if not hasattr(sys, '_cortex_legacy_local'):
    sys._cortex_legacy_local = threading.local()

class ProxyModule(types.ModuleType):
    def __init__(self, name, real_module):
        super().__init__(name)
        object.__setattr__(self, '_real_module', real_module)

    def __getattribute__(self, name):
        if name in ('_real_module', '_initialized', '__class__', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                try:
                    real = object.__getattribute__(self, '_real_module')
                    return getattr(real, name)
                except AttributeError:
                    raise AttributeError(f"ProxyModule object has no attribute '{name}'")
        
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

        val = getattr(self._real_module, name)
        if isinstance(val, types.ModuleType):
            real_name = val.__name__
            alias_name = real_name.replace(self._real_module.__name__, self.__name__, 1)
            if alias_name in sys.modules:
                return sys.modules[alias_name]
            else:
                proxy_sub = ProxyModule(alias_name, val)
                if hasattr(val, '__path__'):
                    proxy_sub.__path__ = val.__path__
                if hasattr(val, '__file__'):
                    proxy_sub.__file__ = val.__file__
                sys.modules[alias_name] = proxy_sub
                object.__setattr__(self, name, proxy_sub)
                return proxy_sub
        return val

    def __setattr__(self, name, value):
        if name in ('_real_module', '_initialized', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            object.__setattr__(self, name, value)
        elif isinstance(value, types.ModuleType):
            object.__setattr__(self, name, value)
        else:
            setattr(self._real_module, name, value)

    def __delattr__(self, name):
        if name in ('_real_module', '_initialized', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            object.__delattr__(self, name)
        elif name in object.__getattribute__(self, '__dict__'):
            object.__delattr__(self, name)
        else:
            delattr(self._real_module, name)

    def __dir__(self):
        return dir(self._real_module)


class LazyAliasLoader(importlib.abc.Loader):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name

    def create_module(self, spec):
        if spec.name == "cortex_extensions" or spec.name.startswith("cortex_extensions."):
            real_module_name = spec.name.replace("cortex_extensions", "babylon60.extensions", 1)
        elif spec.name == self.alias_name:
            real_module_name = self.real_name
        elif spec.name.startswith(self.alias_name + '.'):
            real_module_name = self.real_name + spec.name[len(self.alias_name):]
        else:
            real_module_name = spec.name.replace(self.alias_name, self.real_name, 1)
        real_module = importlib.import_module(real_module_name)
        
        proxy = ProxyModule(spec.name, real_module)
        if hasattr(real_module, '__path__'):
            proxy.__path__ = real_module.__path__
        if hasattr(real_module, '__file__'):
            proxy.__file__ = real_module.__file__
            
        if spec.name.startswith("cortex_extensions."):
            alias_name = spec.name.replace("cortex_extensions", "cortex.extensions", 1)
            sys.modules[alias_name] = proxy
            
        return proxy

    def exec_module(self, module):
        # Support importlib.reload() by reloading the underlying real module only on subsequent calls
        if getattr(module, "_initialized", False):
            if hasattr(module, '_real_module'):
                importlib.reload(module._real_module)
        else:
            module._initialized = True

    def get_code(self, fullname):
        real_module_name = fullname.replace(self.alias_name, self.real_name, 1)
        try:
            import sys
            local_store = getattr(sys, '_cortex_legacy_local', None)
            if local_store is not None:
                local_store.guard = True
            try:
                spec = importlib.util.find_spec(real_module_name)
            finally:
                if local_store is not None:
                    local_store.guard = False
            if spec is not None and spec.loader is not None:
                if hasattr(spec.loader, 'get_code'):
                    return spec.loader.get_code(real_module_name)
        except Exception:
            pass
        return None

    def _get_real_name(self, fullname):
        if fullname == "cortex_extensions" or fullname.startswith("cortex_extensions."):
            return fullname.replace("cortex_extensions", "babylon60.extensions", 1)
        elif fullname == self.alias_name:
            return self.real_name
        elif fullname.startswith(self.alias_name + '.'):
            return self.real_name + fullname[len(self.alias_name):]
        else:
            return fullname.replace(self.alias_name, self.real_name, 1)

    def get_code(self, fullname):
        real_name = self._get_real_name(fullname)
        try:
            spec = importlib.util.find_spec(real_name)
            if spec is not None and spec.loader is not None:
                if hasattr(spec.loader, 'get_code'):
                    return spec.loader.get_code(real_name)
        except Exception:
            pass
        return None

    def get_source(self, fullname):
        real_name = self._get_real_name(fullname)
        try:
            spec = importlib.util.find_spec(real_name)
            if spec is not None and spec.loader is not None:
                if hasattr(spec.loader, 'get_source'):
                    return spec.loader.get_source(real_name)
        except Exception:
            pass
        return None

    def is_package(self, fullname):
        real_name = self._get_real_name(fullname)
        try:
            spec = importlib.util.find_spec(real_name)
            if spec is not None:
                return spec.submodule_search_locations is not None
        except Exception:
            pass
        return False

    def get_filename(self, fullname):
        real_name = self._get_real_name(fullname)
        try:
            spec = importlib.util.find_spec(real_name)
            if spec is not None:
                return spec.origin
        except Exception:
            pass
        return None


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
        if getattr(sys._cortex_legacy_local, 'guard', False):
            return None

        if fullname == "cortex_extensions" or fullname.startswith("cortex_extensions."):
            target_name = fullname.replace("cortex_extensions", "babylon60.extensions", 1)
            sys._cortex_legacy_local.guard = True
            try:
                spec = importlib.util.find_spec(target_name)
                if spec is not None:
                    return importlib.util.spec_from_loader(
                        fullname, LazyAliasLoader(self.alias_name, self.real_name), origin=spec.origin
                    )
            except Exception:
                return None
            finally:
                sys._cortex_legacy_local.guard = False

        if fullname == self.alias_name or fullname.startswith(self.alias_name + '.'):
            if self._has_physical_module(fullname):
                return None
                
            if fullname == self.alias_name:
                real_name = self.real_name
            else:
                real_name = self.real_name + fullname[len(self.alias_name):]
            
            sys._cortex_legacy_local.guard = True
            try:
                spec = importlib.util.find_spec(real_name)
                if spec is None:
                    return None
            except Exception:
                return None
            finally:
                sys._cortex_legacy_local.guard = False

            return importlib.util.spec_from_loader(
                fullname,
                LazyAliasLoader(self.alias_name, self.real_name)
            )
        return None

# Ensure the repository root is in sys.path so babylon60 is discoverable
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Install the proxy in sys.meta_path so that all submodules of cortex
# resolve to babylon60's submodules seamlessly.
if not any(isinstance(f, AliasFinder) and f.alias_name == 'cortex' for f in sys.meta_path):
    sys.meta_path.insert(0, AliasFinder('cortex', 'babylon60'))

# Create the root proxy module and register it in sys.modules
import babylon60

cortex_root = ProxyModule('cortex', babylon60)
cortex_root.__path__ = [os.path.dirname(os.path.abspath(__file__))]
if hasattr(babylon60, '__file__'):
    cortex_root.__file__ = babylon60.__file__

sys.modules['cortex'] = cortex_root
