# Create S3 Bucket
resource "aws_s3_bucket" "gbfs_bucket" {
  bucket = "gbfs-data-storage"
}

resource "aws_iam_role" "lambda_exec" {
  name = "GBFSDataFetcher-role-36uw9y89"
  path = "/service-role/"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

# Create MySQL RDS Instance
resource "aws_db_instance" "mysql" {
  allocated_storage    = 20
  engine               = "mysql"
  engine_version       = "8.0.39"
  instance_class       = "db.t4g.micro"
  username             = "admin"
  password             = var.rds_password
  parameter_group_name = "default.mysql8.0"
  storage_encrypted    = true
  publicly_accessible  = true
  skip_final_snapshot  = true
  copy_tags_to_snapshot = true
  max_allocated_storage = 1000

  vpc_security_group_ids = [aws_security_group.rds_sg.id]
}

# Security Group for RDS
resource "aws_security_group" "rds_sg" {
  name        = "gbfs_rds_sg"
  description = "Allow MySQL access"

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Open to all (not recommended for production)
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Key Pair
resource "tls_private_key" "pk" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = "gbfs"
  public_key = tls_private_key.pk.public_key_openssh
}

# Create EC2 Instance
resource "aws_instance" "grafana_server" {
  ami           = "ami-05576a079321f21f8"
  instance_type = "t2.micro"
  key_name      = "gbfs"

  vpc_security_group_ids = [
    aws_security_group.http_tcp_sg.id
  ]

  user_data = <<EOF
#!/bin/bash
sudo yum install -y https://dl.grafana.com/enterprise/release/grafana-enterprise-11.1.0-1.x86_64.rpm
sudo systemctl enable grafana-server.service
sudo systemctl start grafana-server.service
EOF
}

# Security Group for EC2 Instance
resource "aws_security_group" "http_tcp_sg" {
  name        = "http_tcp_sg"
  description = "Allow HTTP and TCP 3000 access"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "null_resource" "get_pk" {
  depends_on = [ aws_instance.grafana_server ]
  triggers = {
    always_run = timestamp()
  }
  provisioner "local-exec" {
    command = <<EOT
      terraform output -raw private_key > ./web_server.pem
    EOT
  }
}