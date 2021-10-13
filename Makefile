ALL_PYTHON_XARGS=find . -iname "*.py" | xargs
PWD=$(shell pwd)

.PHONY: run

run:
	python3 dataset.py
	streamlit run climate.py

format:
	$(ALL_PYTHON_XARGS) python3 -m black -S
	$(ALL_PYTHON_XARGS) python3 -m autoflake \
		--in-place \
		--remove-unused-variables \
		--remove-all-unused-imports
	$(ALL_PYTHON_XARGS) python3 -m isort