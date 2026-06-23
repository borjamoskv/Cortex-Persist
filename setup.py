from setuptools import Extension, setup

babylon60_native_module = Extension(
    "babylon60_native",
    sources=["babylon60/extensions/native/babylon60_native.c"],
    extra_compile_args=["-O3", "-Wall"],
)

# This setup.py supplements the pyproject.toml to build the C extension
setup(
    name="babylon-60",
    ext_modules=[babylon60_native_module],
)
