
#  GraphRAG DevOps Platform

> End-to-end GraphRAG system with production-grade DevOps pipeline (Docker, Kubernetes, Terraform, Jenkins)

---

##  Overview

This project builds a **Graph-based Retrieval-Augmented Generation (GraphRAG)** system and deploys it using a complete **DevOps workflow**.

It is designed to demonstrate how modern AI systems move from:
**prototype → container → pipeline → scalable deployment**

---

##  Key Highlights

- GraphRAG-based intelligent query system
- Backend API for model interaction
- Frontend interface for user queries
- Fully containerized using Docker
- Kubernetes-ready deployment
- Infrastructure provisioning via Terraform
- CI/CD automation using Jenkins

---

##  System Flow

\`\`\`
User → Frontend → Backend API → GraphRAG Processing → Response
\`\`\`

---

##  Project Structure

\`\`\`
graphrag-devop-project/
│
├── app/                # Core backend logic
├── frontend/           # UI layer
├── k8s/                # Kubernetes configs
├── terraform/          # Infrastructure setup
├── sample_data/        # Example data
│
├── Dockerfile          # Container definition
├── docker-compose.yml  # Multi-service setup
├── Jenkinsfile         # CI/CD pipeline
├── main.py             # Entry point
├── requirements.txt
└── .env.example
\`\`\`

---

##  Tech Stack

- **Language:** Python  
- **Backend:** FastAPI (or similar ASGI framework)  
- **Frontend:** Web UI (inside /frontend)  
- **Containerization:** Docker  
- **Orchestration:** Kubernetes  
- **CI/CD:** Jenkins  
- **Infrastructure:** Terraform  

---

##  Setup

### Clone the repository
\`\`\`bash
git clone https://github.com/Madhusmita111/graphrag-devop-project.git
cd graphrag-devop-project
\`\`\`

---

### Create virtual environment
\`\`\`bash
python -m venv venv
source venv/bin/activate
\`\`\`

Windows:
\`\`\`
venv\Scripts\activate
\`\`\`

---

### Install dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

---

##  Environment Variables

Create a `.env` file using:

\`\`\`bash
cp .env.example .env
\`\`\`

Update values as required.

---

##  Docker Usage

### Build image
\`\`\`bash
docker build -t graphrag-app .
\`\`\`

### Run container
\`\`\`bash
docker run -p 8000:8000 graphrag-app
\`\`\`

### Using docker-compose
\`\`\`bash
docker-compose up --build
\`\`\`

---

##  Kubernetes Deployment

Apply manifests:
\`\`\`bash
kubectl apply -f k8s/
\`\`\`

Check resources:
\`\`\`bash
kubectl get pods
\`\`\`

---

##  Terraform Infrastructure

\`\`\`bash
cd terraform
terraform init
terraform apply
\`\`\`

---

##  CI/CD Pipeline

The project includes a Jenkins pipeline defined in:

\`\`\`
Jenkinsfile
\`\`\`

Typical stages:
- Build
- Containerization
- Deployment

---

##  Run Locally

\`\`\`bash
uvicorn main:app --reload
\`\`\`

Access API docs:
\`\`\`
http://localhost:8000/docs
\`\`\`

---

##  Testing

\`\`\`bash
pytest
\`\`\`

---

##  Why This Project Matters

This project demonstrates:

- Applying **AI (GraphRAG)** in a real system
- Packaging ML systems for production
- Deploying with **modern DevOps tools**
- Designing scalable, modular architecture

---

##  Author

**Madhusmita**  
---
