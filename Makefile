VERSION=0.12
DEB=tmradio-client-gtk-${VERSION}.deb
ZIP=tmradio-client-gtk-${VERSION}.zip
TAR=tmradio-client-gtk-${VERSION}.tar.gz
RELEASE_DIR=/remote/files.tmradio.net/software/client

all: help

help:
	@echo "bdist    build a Python egg"
	@echo "clean    delete temporary files"
	@echo "config   edit your client's config"
	@echo "deb      build a Debian package"
	@echo "install  install the client (using setup.py)"
	@echo "run      run the client in nirmal mode"
	@echo "test     run the client in debug mode"
	@echo "zip      build a source ZIP archive"

config:
	editor $(HOME)/.tmradio-client.yaml

run:
	./bin/tmradio-client 2>&1 | tee client.log

test:
	./bin/tmradio-client 2>&1 | tee client.log

clean:
	rm -f *.zip *.deb *.tar.gz src/tmradio/*.pyc src/tmradio/ui/*.pyc

bdist: clean
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
	zip -qr9 ${ZIP} bin data src Makefile CHANGES COPYING README.md setup.py

tar:
	tar cfz ${TAR} bin data src Makefile CHANGES COPYING README.md setup.py

upload-deb: clean deb zip tar
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${DEB}
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${ZIP}
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${TAR}

install:
	sudo python setup.py install --record install.log

uninstall:
	cat install.log | xargs sudo rm -f

release: clean deb zip
	mv ${DEB} ${ZIP} ${RELEASE_DIR}/
