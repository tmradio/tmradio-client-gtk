#!/usr/bin/env python
# vim: set fileencoding=utf-8:

import glob
from distutils.core import setup

# Files to install:
data_files = [
    ('share/applications', ['data/tmradio.desktop']),
    ('share/doc/tmradio/client', ['CHANGES', 'COPYING', 'README.md']),
    ('share/icons/hicolor/16x16/apps', ['data/icon-16.png']),
    ('share/icons/hicolor/24x24/apps', ['data/icon-24.png']),
    ('share/icons/hicolor/256x256/apps', ['data/icon-256.png']),
    ('share/icons/hicolor/32x32/apps', ['data/icon-32.png']),
    ('share/icons/hicolor/48x48/apps', ['data/icon-48.png']),
    ('share/icons/hicolor/64x64/apps', ['data/icon-64.png']),
    ('share/icons/hicolor/72x72/apps', ['data/icon-72.png']),
    ('share/tmradio-client', glob.glob('data/*.ui')),
]

classifiers = [
    'Development Status :: 4 - Beta', 'Environment :: X11 Applications :: GTK',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Natural Language :: English',
    'Operating System :: Unix',
    'Programming Language :: Python',
    'Topic :: Communications :: Chat',
    'Topic :: Internet',
    'Topic :: Multimedia :: Sound/Audio :: Players',
    ]


setup(
    author = 'Justin Forest',
    author_email = 'hex@umonkey.net',
    classifiers = classifiers,
    data_files = data_files,
    description = 'An Internet radio player with embedded chat client.',
    long_description = 'An Internet radio player with embedded XMPP chat client, Twitter and Podcast aggregator.',
    license = 'Gnu GPL',
    name = 'tmradio-client',
    package_dir = { '': 'src' },
    packages = [ 'tmradio', 'tmradio.ui' ],
    requires = [ 'feedparser', 'gst', 'gtk', 'json', 'pygst', 'pygtk', 'xmpp', 'yaml' ],
    scripts = [ 'bin/tmradio-client' ],
    url = 'http://tmradio.net/',
    version = '0.12'
)
