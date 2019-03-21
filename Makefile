IMAGE_BUILDER_IMAGE = wellcome/image_builder:25
PUBLISH_SERVICE_IMAGE = wellcome/publish_service:60

ROOT = $(shell git rev-parse --show-toplevel)
DOCKER_RUN = $(ROOT)/wellcome/docker_run.py

ACCOUNT_ID = 299497370133


# Build and tag a Docker image.
#
# Args:
#   $1 - Name of the image.
#   $2 - Name of the Dockerfile in the src directory
#
define build_image
	$(DOCKER_RUN) --dind -- $(IMAGE_BUILDER_IMAGE) \
		--name=$(1) \
		--build-arg GIT_COMMIT="$(shell git log -1 --pretty=format:'%h -- %ai -- %an -- %s')" \
		--path=src/$(2).Dockerfile
endef


# Publish a Docker image to ECR, and put its associated release ID in S3.
#
# Args:
#   $1 - Name of the Docker image.
#
define publish_service
	$(DOCKER_RUN) \
	    --aws --dind -- \
	    $(PUBLISH_SERVICE_IMAGE) \
			--project_id=archivematica \
			--service_id=$(1) \
			--account_id=$(ACCOUNT_ID) \
			--region_id=eu-west-1 \
			--namespace=uk.ac.wellcome
endef


dashboard-build:
	$(call build_image,archivematica_dashboard,dashboard)

dashboard-publish: dashboard-build
	$(call publish_service,archivematica_dashboard)

mcp_client-build:
	$(call build_image,archivematica_mcp_client,MCPClient)

mcp_client-publish: mcp_client-build
	$(call publish_service,archivematica_mcp_client)

mcp_server-build:
	$(call build_image,archivematica_mcp_server,MCPServer)

mcp_server-publish: mcp_server-build
	$(call publish_service,archivematica_mcp_server)
