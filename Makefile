VERSION=0.12
DEB=tmradio-client-gtk-${VERSION}.deb
ZIP=tmradio-client-gtk-${VERSION}.zip
RELEASE_DIR=/remote/files.tmradio.net/software/client

all: help

help:
	@echo "bdist    build a Python egg"
	@echo "clean    delete temporary files"
	@echo "config   edit your client's config"
	@echo "deb      build a Debian package"
	@echo "debug    run the client in debug mode (lots of jabber output)"
	@echo "install  install the client (using setup.py)"
	@echo "test     run the client in normal mode"
	@echo "zip      build a source ZIP archive"

config:
	editor $(HOME)/.tmradio-client.yaml

test:
	./bin/tmradio-client

debug:
	./bin/tmradio-client --debug

clean:
	rm -f *.zip *.deb *.tar.gz

bdist:
	python setup.py bdist
	mv dist/*gz ./
	rm -rf build dist

deb: bdist
	rm -rf *.deb debian/usr
	cat debian/DEBIAN/control.in | sed -e "s/VERSION/${VERSION}/g" > debian/DEBIAN/control
	tar xfz tmradio-client-*.tar.gz -C debian
	mv debian/usr/local/* debian/usr/
	rm -rf debian/usr/local
	fakeroot dpkg -b debian ${DEB}
	rm -rf debian/usr debian/DEBIAN/control

zip:
	zip -r9 ${ZIP} bin data Makefile CHANGES COPYING README.md setup.py

upload-deb: deb zip
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${DEB}
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${ZIP}

install:
	sudo python setup.py install

release: clean deb zip
	mv ${DEB} ${ZIP} ${RELEASE_DIR}/
