import os
import sys


def Run(*args, **kwargs):
    if '--tk' in sys.argv or os.environ.get('TMCLIENT') == 'tk':
        import tmradio.ui.tk
        return tmradio.ui.tk.Run(*args, **kwargs)
    elif '--text' in sys.argv or os.environ.get('TMCLIENT') == 'text':
        import tmradio.ui.text
        return tmradio.ui.text.Run(*args, **kwargs)
    else:
        import tmradio.ui.gnome
        return tmradio.ui.gnome.Run(*args, **kwargs)
