version=0.14.7-pre
avconv_exists := $(shell which avconv)
ffmpeg_exists := $(shell which ffmpeg)

all:
ifdef avconv_exists
	@echo "Program 'avconv' found, using that..."
	sed -i 's/ffmpeg/avconv/g' castawesome.py
else
	@echo "Couldn't find 'avconv'."
ifdef ffmpeg_exists
	@echo "Program 'ffmpeg' found, using that..."
	sed -i 's/avconv/ffmpeg/g' castawesome.py
else
	@echo "Couldn't find necessary tools. Install 'avconv' or 'ffmpeg'."
endif
endif
	./castawesome.py test

install:
	mkdir -p /usr/local/share/castawesome/ui
	mkdir -p /usr/local/share/castawesome/doc
	cp *.ui /usr/local/share/castawesome/ui
	cp *.png /usr/local/share/castawesome/ui
	cp README AUTHORS NEWS COPYING /usr/local/share/castawesome/doc
	cp castawesome.py /usr/local/bin/castawesome
	cp uninstall_castawesome.sh /usr/local/bin/uninstall_castawesome
	cp Castawesome.desktop /usr/local/share/applications
	chmod +x /usr/local/bin/castawesome /usr/local/bin/uninstall_castawesome
	chmod +r /usr/local/share/castawesome/ui/*.png

uninstall:
	rm -rf /usr/local/share/castawesome
	rm -f /usr/local/bin/castawesome /usr/local/bin/uninstall_castawesome
	rm -f /usr/local/share/applications/Castawesome.desktop

use_avconv:
	sed -i 's/ffmpeg/avconv/g' castawesome.py

use_ffmpeg:
	sed -i 's/avconv/ffmpeg/g' castawesome.py

package:
	rm -rf castawesome*.tar.gz castawesome/
	rsync -av --progress ./ castawesome --exclude castawesome --exclude .git
	tar zczf castawesome-$(version).tar.gz castawesome

clean:
	rm -f castawesome*.tar.gz
