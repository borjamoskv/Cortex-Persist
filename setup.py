from setuptools import setup, Extension

cortex_native_module = Extension(
    'cortex_native',
    sources=['cortex/extensions/native/cortex_native.c'],
    extra_compile_args=['-O3', '-Wall'],
)

# This setup.py supplements the pyproject.toml to build the C extension
setup(
    name='cortex-persist',
    ext_modules=[cortex_native_module],
)
