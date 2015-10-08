from setuptools import setup, find_packages

setup(
    name='janeus',
    version='1.4',
    packages=find_packages(),
    url='http://github.com/jonge-democraten/janeus/',
    author='Jonge Democraten',
    include_package_data=True,
    license='MIT',
    install_requires=['pyldap>=2.4.20'],
)
