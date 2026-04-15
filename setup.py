from distutils.core import setup
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


setup(
    name='cachian',         # How you named your package folder (MyLib)
    packages=['cachian'],   # Chose the same as "name"
    version='0.6',      # Start with a small number and increase it with every change you make
    # Chose a license from here: https://help.github.com/articles/licensing-a-repository
    license='MIT AND (Apache-2.0 OR BSD-2-Clause)',
    # Give a short description about your library
    description='Python lru_cache but with TTL',
    long_description_content_type='text/markdown',
    long_description=long_description,
    author='Ian Teoh',                   # Type in your name
    author_email='ian.teohsc@gmail.com',      # Type in your E-Mail
    # Provide either the link to your github or to your website
    url='https://github.com/ianteohsc/cachian',
    # I explain this later on
    download_url='https://github.com/ianteohsc/cachian/archive/refs/tags/v0.2.tar.gz',
    # Keywords that define your package best
    keywords=['LRU', 'cache', 'ttl'],
    install_requires=[            # I get to this in a second
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
)
