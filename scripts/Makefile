.DEFAULT_GOAL := help

.PHONY: jn
jn: ## Open Jupyter notebook in the venv_land
	. ../venv_land/bin/activate && jupyter notebook


.PHONY: help
help: ## Show this help message and exit
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'