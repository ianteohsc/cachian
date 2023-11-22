from distutils.core import setup
setup(
  name = 'cachian',         # How you named your package folder (MyLib)
  packages = ['cachian'],   # Chose the same as "name"
  version = '0.2',      # Start with a small number and increase it with every change you make
  license='MIT',        # Chose a license from here: https://help.github.com/articles/licensing-a-repository
  description = 'Python lru_cache but with TTL',   # Give a short description about your library
  author = 'Ian Teoh',                   # Type in your name
  author_email = 'ian.teoh@gmail.com',      # Type in your E-Mail
  url = 'https://github.com/ianteohsc/cachian',   # Provide either the link to your github or to your website
  download_url = 'https://github.com/ianteohsc/cachian/archive/refs/tags/v0.2.tar.gz',    # I explain this later on
  keywords = ['LRU', 'cache', 'ttl'],   # Keywords that define your package best
  install_requires=[            # I get to this in a second
      ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Libraries :: Python Modules',
    'License :: OSI Approved :: MIT License',   # Again, pick a license
    'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
  ],
)