# Frontend
OPENAPI_URL = https://dev-svinka.zvonok.in/openapi.json
GENERATOR = typescript-axios
OUTPUT_DIR = src/fastApi/

beauty-front:
	npm run beauty
generate-api:
	# skip-validate-spec - due to webhooks
	docker run --rm -v ${PWD}:/localSvinka openapitools/openapi-generator-cli generate \
	  --skip-validate-spec \
	  -i $(OPENAPI_URL) \
	  -g $(GENERATOR) \
	  -o /localSvinka/$(OUTPUT_DIR)