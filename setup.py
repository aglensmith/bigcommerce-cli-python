import os
from setuptools import setup, find_packages

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

VERSION = '0'

setup(
    name='bigcli',
    version=VERSION,
    entry_points={
        'console_scripts': [
            'bigcli = bigcli.cli:main',
        ],
    },
    packages=find_packages(),
    install_requires=['bigcommerce @ git+https://github.com/aglensmith/bigcommerce-api-python.git@bigcli#egg=bigcommerce'],
    url='https://github.com/aglensmith/bigcommerce-cli-python',
    author='Austin Smith',
    description='A CLI tool for BigCommerce',
    long_description=read('README.md'),
    license='MIT',
    keywords=['bigcommerce', 'api', 'cli', 'client', 'v3', 'v2'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Office/Business',
        'Topic :: Internet :: WWW/HTTP',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.9'
    ]
)