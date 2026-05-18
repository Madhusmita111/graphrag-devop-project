variable "region" {
  default = "ap-south-1"
}

variable "instance_type" {
  default = "t3.small" 
}


variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "graphrag-devops"
}

