all:

docs/mora.db.html: mora/db/__init__.py
	docco mora/db/__init__.py
	sed -e 's/__init__\.py/mora\/db\/__index__.py/g' < docs/__init__.html > docs/mora.db.html

docs/mora.rest.html: mora/rest/__init__.py
	docco mora/rest/__init__.py
	sed -e 's/__init__\.py/mora\/rest\/__index__.py/g' < docs/__init__.html > docs/mora.rest.html

docs: docs/mora.db.html docs/mora.rest.html
	rm docs/__init__.html

.PHONY: test
test:
	bin/test.py /opt/local/share/google_appengine mora test
