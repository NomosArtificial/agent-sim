.PHONY: deploy_modal_falcon_40b

deploy_modal_falcon_40b:
	@echo "Deploying modal_falcon_40b"
	@cd models/modal_falcon_40b && poetry run modal deploy model.py
