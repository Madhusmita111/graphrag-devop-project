data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "tls_private_key" "k3s_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "k3s_key_pair" {
  key_name   = "${var.project_name}-key"
  public_key = tls_private_key.k3s_key.public_key_openssh
}

resource "local_file" "private_key" {
  content         = tls_private_key.k3s_key.private_key_pem
  filename        = "${path.module}/${var.project_name}-key.pem"
  file_permission = "0400"
}

resource "aws_security_group" "k3s_sg" {
  name        = "${var.project_name}-k3s-sg"
  description = "Security group for K3s server"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  ingress {
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Kubernetes API"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "k3s_role" {
  name = "${var.project_name}-k3s-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.k3s_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "k3s_profile" {
  name = "${var.project_name}-k3s-profile"
  role = aws_iam_role.k3s_role.name
}

resource "aws_instance" "k3s_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  key_name      = aws_key_pair.k3s_key_pair.key_name
  
  vpc_security_group_ids = [aws_security_group.k3s_sg.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.k3s_profile.name

  user_data = <<-EOF
              #!/bin/bash
              apt-get update -y
              
              # Enable IMDSv2 token for querying public IP (used for TLS SAN)
              TOKEN=$$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
              PUBLIC_IP=$$(curl -s -H "X-aws-ec2-metadata-token: $$TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
              
              # Install k3s with the EC2 public IP configured as a TLS Subject Alternative Name (SAN)
              curl -sfL https://get.k3s.io | sh -s - --tls-san $$PUBLIC_IP
              
              # Wait for node and kubeconfig to be ready
              sleep 15
              chmod 644 /etc/rancher/k3s/k3s.yaml
              EOF

  tags = {
    Name = "${var.project_name}-k3s-server"
  }
}

output "k3s_server_public_ip" {
  value = aws_instance.k3s_server.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the K3s server"
  value       = "ssh -i ${var.project_name}-key.pem ubuntu@${aws_instance.k3s_server.public_ip}"
}

output "kubeconfig_command" {
  description = "Command to copy kubeconfig file from the server to your local machine"
  value       = "scp -i ${var.project_name}-key.pem ubuntu@${aws_instance.k3s_server.public_ip}:/etc/rancher/k3s/k3s.yaml ./k3s.yaml"
}
