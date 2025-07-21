import importlib.util
import os.path
from setuptools import setup

setup_directory = os.path.abspath(os.path.dirname(__file__))

version_file_path = os.path.join(setup_directory, 'sampledb', 'version.py')
spec = importlib.util.spec_from_file_location("version", version_file_path)
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)

setup(
    version=version.__version__,
)
