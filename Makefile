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
	zip -r9 ${ZIP} bin doc share Makefile CHANGES COPYING README.md

upload-deb: deb zip
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${DEB}
	-googlecode_upload.py -s "Version ${VERSION} of the GTK+ client for tmradio.net" -p umonkey-tools -l tmradio ${ZIP}

install:
	sudo python setup.py install

release:
	make -C ../.. update-packages
