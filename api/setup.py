from setuptools import setup

with open('README', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
   name="scalar",
   version="1.0",
   license="MIT",

   description='Scalar API implementation',
   long_description=long_description,

   author='googer_',
   url="https://github.com/Def-Try/scalar",

   packages=['scalar',
             'scalar.protocol',
             'scalar.protocol.encryption',
             'scalar.protocol.packets',
             'scalar.protocol.socket',
             'scalar.server',
             'scalar.server.implementations',
             'scalar.server.implementations.scalar0',
             'scalar.client',
             'scalar.client.implementations'],
   install_requires=['cryptography'],
)