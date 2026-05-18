resource "aws_ecr_repository" "graphrag_api" {
  name                 = "graphrag-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
