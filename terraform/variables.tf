variable "access_key" {
  default = ""
}

variable "secret_key" {
  default = ""
}

variable "rds_password" {
  default = ""
}

variable "lambda_function_arn" {
  default = "arn:aws:lambda:us-east-1:164008106637:function:GBFSDataFetcher"
}

variable "lambda_function_name" {
  default = "GBFSDataFetcher"
}