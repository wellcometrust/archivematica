define _terraform_run
	docker run --rm \
		--volume ~/.aws:/root/.aws \
		--volume $(CURDIR):$(CURDIR) \
		--workdir $(CURDIR)/terraform \
		hashicorp/terraform:0.11.11
endef


tf-plan:
	$(_terraform_run) init
	$(_terraform_run) get
	$(_terraform_run) plan -out terraform.plan


tf-apply:
	$(_terraform_run) apply terraform.plan
