.PHONY: help

# primehub ce with specific commit sha: https://github.com/InfuseAI/primehub/commit/62a729a3518b309fb09a637c0ac36f41eff66cdc
PRIMEHUB_SHA := 25c117a85b0969230a7ed0cee3a2f4728e74f08e

help:
	@echo "Primehub Admission"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "targets:"
	@echo ""
	@echo "  update-shared-lib"

update-shared-lib:
	@echo "Updating primehub_admission/primehub_utils.py"; \
	curl -s -o primehub_admission/primehub_utils.py -L "https://raw.githubusercontent.com/InfuseAI/primehub/$(PRIMEHUB_SHA)/chart/scripts/jupyterhub/config/primehub_utils.py"

get-primehub-sha:
	@printf $(PRIMEHUB_SHA)
