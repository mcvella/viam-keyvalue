.PHONY: test clean

test:
	PYTHONPATH=. pytest test/ -v

clean:
	rm -rf /tmp/viam/keyvalue/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete 