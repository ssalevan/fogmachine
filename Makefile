TOP_DIR:=$(shell pwd)

all: clean build

build:
	python setup.py build -f
        
install: build
	python setup.py install -f

clean:
	find . -name "*~" -exec rm -f '{}' \;
	-rm -rf build rpm-build dist
	-rm -f MANIFEST
	-rm -f *.pyc
	-rm -f *.pyo
	-rm -f fogmachine/*.pyc
	-rm -f fogmachine/*.pyo
	-rm -f *.tmp
	-rm -f *.log
	-rm -f *.sqlite

sdist: clean
	python setup.py sdist
        
rpms: clean sdist
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_sourcedir  %{_topdir}" \
	-ba fogmachine.spec
