# aws cloudformation delete-stack --stack-name LangBuilderAppStack
aws ecr delete-repository --repository-name langbuilder-backend-repository --force
# aws ecr delete-repository --repository-name langbuilder-frontend-repository --force
# aws ecr describe-repositories --output json | jq -re ".repositories[].repositoryName"