import importlib.util
from setuptools import setup, find_packages
import os.path

setup_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(setup_directory, 'README.md')) as readme_file:
    long_description = readme_file.read()

with open(os.path.join(setup_directory, 'requirements.txt')) as requirements_file:
    requirements = requirements_file.readlines()

version_file_path = os.path.join(setup_directory, 'sampledb', 'version.py')
spec = importlib.util.spec_from_file_location("version", version_file_path)
version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version)


setup(
    name='sampledb',
    version=version.__version__,
    description='A sample and measurement metadata database',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sciapp/sampledb',
    author='Florian Rhiem',
    author_email='f.rhiem@fz-juelich.de',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Framework :: Flask',
        'Topic :: Scientific/Engineering',
    ],
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=requirements,
    package_data={
        'sampledb': [
            'static/*/*.*',
            'static/*/*/*.*',
            'static/*/*/*/*.*'
        ],
        'sampledb.logic': [
            'unit_definitions.txt'
        ],
        'sampledb.frontend': [
            'templates/*/*.*',
            'templates/*/*/*.*',
            'templates/*/*/*/*.*'
        ]
    }
)
