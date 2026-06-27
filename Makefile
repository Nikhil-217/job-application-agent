.PHONY: install playground run

install:
	python -m venv .venv
	.venv/Scripts/pip install -r requirements.txt

playground:
	.venv/Scripts/python app.py

run:
	.venv/Scripts/adk web job_agent
