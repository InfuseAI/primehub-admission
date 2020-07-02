.PHONY: help

help:
	@echo "Primehub Admission"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "targets:"
	@echo ""
	@echo "  update-shared-lib"

update-shared-lib:
	@echo "Updating src/primehub_utils.py"; \
	commit_sha=62a729a3518b309fb09a637c0ac36f41eff66cdc; \
	curl -s -o src/primehub_utils.py -L https://raw.githubusercontent.com/InfuseAI/primehub/$${commit_sha}/chart/scripts/jupyterhub/config/primehub_utils.py
