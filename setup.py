from setuptools import setup
import os.path

setup_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(setup_directory, 'README.md')) as readme_file:
    long_description = readme_file.read()

setup(
    name='sampledb',
    version='0.8.0',
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
    packages=['sampledb'],
)
