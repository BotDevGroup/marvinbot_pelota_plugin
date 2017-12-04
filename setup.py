from distutils.core import setup
from setuptools import find_packages

REQUIREMENTS = [
    'marvinbot',
    'bs4'
]

setup(name='marvinbot-pelota-plugin',
      version='0.1',
      description='Dominican Republic Baseball Standings',
      author='Conrado Reyes',
      author_email='coreyes@gmail.com',
      url='',
      packages=[
        'marvinbot_pelota_plugin',
      ],
      package_dir={
        'marvinbot_pelota_plugin':'marvinbot_pelota_plugin'
      },
      zip_safe=False,
      include_package_data=True,
      package_data={'': ['*.ini']},
      install_requires=REQUIREMENTS,
      dependency_links=[
          'git+ssh://git@github.com:BotDevGroup/marvin.git#egg=marvinbot',
      ],
)
