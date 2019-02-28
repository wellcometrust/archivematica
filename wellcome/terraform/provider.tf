provider "aws" {
  region  = "eu-west-1"
  version = "2.0.0"

  assume_role {
    role_arn = "arn:aws:iam::299497370133:role/admin"
  }
}
