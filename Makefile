version=0.12.9

all:
	./castawesome.py test

install:
	mkdir -p /usr/local/share/castawesome/ui
	mkdir -p /usr/local/share/castawesome/doc
	cp *.ui /usr/local/share/castawesome/ui
	cp README AUTHORS NEWS COPYING /usr/local/share/castawesome/doc
	cp castawesome.py /usr/local/bin/castawesome
	cp uninstall_castawesome.sh /usr/local/bin/uninstall_castawesome
	cp Castawesome.desktop /usr/local/share/applications
	chmod +x /usr/local/bin/castawesome /usr/local/bin/uninstall_castawesome

uninstall:
	rm -rf /usr/local/share/castawesome
	rm -f /usr/local/bin/castawesome /usr/local/bin/uninstall_castawesome
	rm -f /usr/local/share/applications/Castawesome.desktop

package:
	rm -f castawesome*.tar.gz
	tar czf castawesome-$(version).tar.gz *

clean:
	rm -f castawesome*.tar.gz
