check:
	black --check invoicez
	isort --check-only invoicez
	mypy invoicez
	flake8 --count invoicez
	pylint invoicez
