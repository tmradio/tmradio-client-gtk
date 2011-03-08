VERSION=0.12
DEB=tmradio-client-gtk-${VERSION}.deb
ZIP=tmradio-client-gtk-${VERSION}.zip

all: zip

config:
	editor $(HOME)/.tmradio-client.yaml

test:
	./bin/tmradio-client

debug:
	./tmradio-client --debug

clean:
	rm -f *.zip *.deb

deb:
	rm -rf *.deb debian/usr
	cat debian/DEBIAN/control.in | sed -e "s/VERSION/${VERSION}/g" > debian/DEBIAN/control
	mkdir -p debian/usr
	cp -R bin share debian/usr/
	cp -R doc debian/usr/share/
	sudo chown -R root:root debian/usr
	dpkg -b debian ${DEB}
	sudo rm -rf debian/usr debian/DEBIAN/control

zip:
	zip -r9 ${ZIP} bin doc share Makefile CHANGES COPYING README.md

upload-deb: deb zip
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${DEB}
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${ZIP}

install: deb
	sudo dpkg -i ${DEB}

release:
	make -C ../.. update-packages

bdist:
	python setup.py bdist
	rm -rf build
