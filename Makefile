check:
	black --check invoicez tests
	isort --check-only invoicez tests
	mypy invoicez tests
	flake8 --count invoicez tests
	pylint invoicez tests
