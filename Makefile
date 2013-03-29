version=0.12.5

all:
	./castawesome.py test

install:
	mkdir -p /usr/local/share/castawesome/ui
	mkdir -p /usr/local/share/castawesome/doc
	cp *.ui /usr/local/share/castawesome/ui
	cp README AUTHORS NEWS COPYING /usr/local/share/castawesome/doc
	cp castawesome.py /usr/local/bin/castawesome
	cp Castawesome.desktop /usr/local/share/applications

uninstall:
	rm -rf /usr/local/share/castawesome
	rm -f /usr/local/bin/castawesome
	rm -f /usr/local/share/applications/Castawesome.desktop

package:
	rm -f castawesome*.tar.gz
	tar czf castawesome-$(version).tar.gz *

clean:
	rm -f castawesome*.tar.gz
