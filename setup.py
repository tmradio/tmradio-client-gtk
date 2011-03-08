#!/usr/bin/env python
# vim: set fileencoding=utf-8:

import glob
from distutils.core import setup

# Files to install:
inst_share_ui = glob.glob('share/tmradio-client/*.ui')
inst_desktop = [ 'share/applications/tmradio.desktop' ]

inst_icons = [ 'share/icons/hicolor/48x48/apps/tmradio-client.png' ]
inst_icons_256 = [ 'share/icons/hicolor/256x256/apps/tmradio-client.png' ]
inst_icons_72 = [ 'share/icons/hicolor/72x72/apps/tmradio-client.png' ]
inst_icons_64 = [ 'share/icons/hicolor/64x64/apps/tmradio-client.png' ]
inst_icons_48 = [ 'share/icons/hicolor/48x48/apps/tmradio-client.png' ]
inst_icons_32 = [ 'share/icons/hicolor/32x32/apps/tmradio-client.png' ]
inst_icons_24 = [ 'share/icons/hicolor/24x24/apps/tmradio-client.png' ]
inst_icons_16 = [ 'share/icons/hicolor/16x16/apps/tmradio-client.png' ]

data_files = [
    ('share/tmradio-client', inst_share_ui),
    ('share/icons/hicolor/48x48/apps', inst_icons ),
    ('share/icons/hicolor/32x32/apps', inst_icons_32 ),
    ('share/icons/hicolor/16x16/apps', inst_icons_16 ),
]

packages = []

setup(
    name = 'tmradio-client',
    version = '0.12',
    package_dir = { '': 'src' },
    packages = packages,
    description = 'media player',
    author = 'Justin Forest',
    author_email = 'hex@umonkey.net',
    url = 'http://tmradio.net/',
    scripts = [ 'bin/tmradio-client' ],
    data_files = data_files
)
