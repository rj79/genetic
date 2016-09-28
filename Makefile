VENV=venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
REQ=requirements.txt

DONE_VENV=.done_venv
DONE_REQS=.done_requirements
DONE_UPGRADE_PIP=.done_upgrade_pip
DONE_FILES += $(DONE_VENV)
DONE_FILES += $(DONE_REQS)
DONE_FILES += $(DONE_UPGRADE_PIP)

all: $(DONE_REQS)
	$(PYTHON) example.py

test: $(DONE_REQS)
	$(PYTHON) gengine.py

$(DONE_REQS): $(DONE_UPGRADE_PIP)
	$(PIP) install -r $(REQ) && touch $@

$(DONE_UPGRADE_PIP): $(DONE_VENV)
	$(PIP) install pip --upgrade && touch $@

$(DONE_VENV): requirements.txt
	python3 -m venv $(VENV) && touch $@

clean:
	rm -rf $(VENV) $(DONE_FILES)
