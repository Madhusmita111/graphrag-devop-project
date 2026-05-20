pipeline {
    agent any

    environment {
        AWS_REGION         = 'ap-south-1'
        AWS_ACCOUNT_ID     = '933428634281'
        ECR_REPO_NAME      = 'graphrag-api'
        ECR_REGISTRY       = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_TAG          = "latest" // Or use "${env.BUILD_NUMBER}"
        KUBECONFIG_CRED_ID = 'k3s-kubeconfig' // Jenkins credential ID for K3s kubeconfig
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm
            }
        }

        stage(' Lint & Verify') {
                echo 'Running linting and code validation...'
                sh 'python3 -m py_compile main.py app/*.py'
            }
        }

        stage(' Build Image') {
            steps {
                echo 'Building backend Docker image...'
                script {
                    dockerImage = docker.build("${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}", ".")
                }
            }
        }

        stage(' Push to AWS ECR') {
            steps {
                echo 'Authenticating and pushing image to AWS ECR...'
                script {
                    // Use AWS CLI to authenticate docker daemon to ECR
                    sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}"
                    // Push the built image
                    sh "docker push ${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"
                }
            }
        }

        stage('Deploy to Kubernetes (K3s)') {
            steps {
                echo 'Deploying to K3s cluster...'
                withCredentials([file(credentialsId: KUBECONFIG_CRED_ID, variable: 'KUBECONFIG')]) {
                    sh 'kubectl --kubeconfig=$KUBECONFIG apply -f k8s/neo4j.yaml'
                    
                    // Substitute the ECR image registry inside api.yaml dynamically if needed
                    sh """
                    sed -i "s|933428634281.dkr.ecr.us-east-1.amazonaws.com|${ECR_REGISTRY}|g" k8s/api.yaml
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/api.yaml
                    """
                    
                    echo 'Waiting for deployment to rollout...'
                    sh 'kubectl --kubeconfig=$KUBECONFIG rollout status deployment/graphrag-api --timeout=120s'
                }
            }
        }
    }

    post {
        success {
            echo 'CI/CD Pipeline Completed Successfully! Enterprise GraphRAG is deployed!'
        }
        failure {
            echo 'Pipeline Failed. Checking logs...'
        }
    }
}
