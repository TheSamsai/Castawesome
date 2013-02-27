
all:
	./castawesome.py test

install:
	mkdir -p /usr/local/share/castawesome/ui
	mkdir -p /usr/local/share/castawesome/doc
	cp *.ui /usr/local/share/castawesome/ui
	cp README AUTHORS NEWS COPYING /usr/local/share/castawesome/doc
	cp castawesome.py /usr/local/bin/castawesome

package:
	rm -f castawesome.tar.gz
	tar czf castawesome.tar.gz *

clean:
	rm -f castawesome.tar.gz
