.PHONY: test test-unit test-integration test-e2e demo clean

# Run all tests
test:
	python3 -m unittest discover -s tests -v

# Run unit tests only
test-unit:
	python3 -m unittest discover -s tests/unit -v

# Run integration tests only
test-integration:
	python3 -m unittest discover -s tests/integration -v

# Run E2E compliance tests only
test-e2e:
	python3 -m unittest discover -s tests/e2e -v

# Run the automated demo script
demo:
	./run_demo.sh

# Reset runtime environment files
clean:
	rm -rf logs backups backup_schedules.txt test-folder cli/config.py.bak
