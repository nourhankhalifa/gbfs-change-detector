### Architecture Overview

The **GBFS Change Detector** is built using an AWS Lambda function written in Python. It is designed to fetch and process real-time data from General Bikeshare Feed Specification (GBFS) endpoints of bike-sharing providers. The architecture leverages AWS services like RDS for structured data persistence, providing a scalable and serverless solution, Grafana for monitoring, GitHub workflows for automationg the infrastructure provisioning and Lambda function deployment.
<img width="1239" alt="Screenshot 2025-01-13 at 2 48 57 AM" src="https://github.com/user-attachments/assets/c402e71d-ba35-46e7-a03e-431ab90ae7af" />

---

### Key Components

1. **AWS Lambda**:
   - The core compute service that executes the Python script periodically using EventBridge.
   - Configured with environment variables to securely pass credentials and configuration details, such as the RDS database password and provider details.

2. **Data Collection**:
   - The script fetches GBFS data from multiple providers specified in the `providers` environment variable. Each provider includes a name and URL for its GBFS feed.
   - Specific feeds (e.g., `station_status`) are processed to extract statistics like the total number of available bikes and docks.

3. **Amazon RDS (Relational Database Service)**:
   - RDS MySQL is used to store processed statistics, enabling advanced querying and integration with visualization tools like Grafana.
   - The Lambda function connects to RDS using the `pymysql` library, and tables are created or updated dynamically if they do not already exist.

---

### Data Flow

1. **Fetching Data**:
   - The Lambda function fetches data from GBFS endpoints via HTTP requests.
   - The data includes metadata about stations, available bikes, and docks.

2. **Processing and Storage**:
   - Extracted statistics (e.g., total bikes and docks) are saved to an RDS MySQL database with timestamps for historical tracking.

3. **Environment Configuration**:
   - Environment variables (`providers`, `rds_password`, etc.) are used to dynamically configure the function, making it highly adaptable without code changes.

4. **Output**:
   - The processed data in RDS is used for visualization via Grafana, enabling real-time monitoring and trend analysis.

---

### Infrastructure Overview

The infrastructure for the GBFS Change Detector project is fully automated using Terraform, enabling seamless deployment and management of resources on AWS. It is designed to efficiently fetch, process, and visualize GBFS data from multiple providers while ensuring scalability and robustness.

---

### Key Components

1. **Amazon RDS (MySQL)**:
   - A managed MySQL database is provisioned to store processed statistics extracted from the GBFS data. It is configured with encryption, publicly accessible settings, and automated scaling options.
   - A security group is applied to allow MySQL access on port 3306 from all IPs (not recommended for production but useful for testing and development).

2. **AWS Lambda**:
   - An IAM role is created with permissions to allow a Lambda function to fetch data from GBFS providers, store raw JSON in S3, and write processed stats to the RDS database.
   - The Lambda function is triggered every 30 minutes using an EventBridge rule.

3. **Grafana on EC2**:
   - An EC2 instance is configured to host Grafana for data visualization. The instance runs a free-tier `t2.micro` instance with Grafana installed via user data script.
   - Grafana is automatically configured with dashboards and a MySQL datasource to query the RDS database for statistics.
   - Security groups allow HTTP (port 80) and Grafana’s default port (3000) for user access, as well as SSH (port 22) for administrative access restricted to the current user’s IP.

4. **EventBridge**:
   - A CloudWatch EventBridge rule is set up to trigger the Lambda function every 30 minutes. This ensures periodic data fetching and processing without manual intervention.

5. **Key Pair**:
   - A dynamically generated SSH key pair is used to securely connect to the EC2 instance. The private key is stored locally for secure access.

6. **File and Remote Provisioning**:
   - Custom Grafana dashboards and datasource configurations are uploaded to the EC2 instance using Terraform `null_resource` and `remote-exec` provisioners. These files are integrated into Grafana, which is restarted to apply the configurations automatically.

---

### CI/CD Pipelines

The project includes two automated GitHub workflows for seamless deployment and infrastructure management. These workflows ensure that both the Lambda function and the underlying AWS infrastructure are consistently built and updated, reducing the chance of human error and promoting a streamlined CI/CD process.

---

#### **Lambda Deployment Workflow (`ci.yml`)**

This workflow is triggered whenever changes are pushed to the `main` branch and affect files in the `lambda/` directory or the workflow file itself. It automates the build and deployment of the Lambda function:

1. **Checkout Code**:
   - Fetches the latest code from the repository to prepare for deployment.

2. **Python Setup and Dependency Installation**:
   - Installs Python 3.9 and packages required for the Lambda function.
   - Packages the Lambda function code and its dependencies into a ZIP file.

3. **Create or Update Lambda Function**:
   - Checks if the Lambda function already exists using `aws lambda get-function`.
   - If it exists, updates the function code and environment variables (such as the RDS password and provider list).
   - If it doesn’t exist, creates a new Lambda function with the specified configuration.

4. **To Dynamically Add or Update Providers**:
    - Update the providers environment variable in your github repository variables.

---

#### **Terraform Infrastructure Workflow (`infra.yml`)**

This workflow is triggered whenever changes are pushed to the `main` branch that affect the `terraform/` directory or the workflow file itself. It automates the provisioning and updating of AWS infrastructure using Terraform:

1. **Checkout Code**:
   - Fetches the latest Terraform configuration files from the repository.

2. **Terraform Setup**:
   - Installs and initializes the specified Terraform version to manage the infrastructure.

3. **Terraform Plan**:
   - Creates an execution plan (`tfplan`) to preview the changes that will be made to the infrastructure.
   - Ensures the workflow respects the `rds_password` secret by securely injecting it as a variable.

4. **Terraform Apply**:
   - Applies the Terraform plan to provision or update AWS resources, such as the S3 bucket, RDS database, and EC2 instance.

By managing infrastructure as code, this workflow ensures reproducibility, security, and consistency in the deployment environment.


---

## Repository Structure

```
.
|-- lambda/                  # Python scripts for AWS Lambda functions
|   |-- lambda_function.py   # Main Lambda function for fetching and processing GBFS data
|   |-- requirements.txt     # Pyhon script required libraries 
|-- terraform/               # Terraform configurations for infrastructure provisioning
|   |-- main.tf              # Main infrastructure definition
|   |-- variables.tf         # Input variables for Terraform
|   |-- outputs.tf           # Output definitions for Terraform resources
|   |-- provider.tf          # Terraform provider
|   |-- dashboard.json       # Dashboard template
|   |-- dashboard.yaml       # Dashboard provider template
|-- .github/workflows/       # GitHub Actions CI/CD workflows
|-- README.md                # Project documentation
```

---

## Manual Setup
To manually execute the scripts without using the pipelines, please follow these steps:

### Prerequisites

- **AWS CLI**: Installed and configured with necessary credentials.
- **Terraform**: Installed for provisioning infrastructure.
- **Python 3.9**: Required for running Lambda scripts locally.
- **MySQL Database**: Amazon RDS configured as the database backend.
- **Grafana**: Installed and accessible for dashboard visualization.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nourhankhalifa/gbfs-change-detector.git
   cd gbfs-change-detector
   ```

2. Set up Python environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Provision infrastructure using Terraform:
   ```bash
   cd terraform
   terraform init
   terraform apply -var='rds_password=your_rds_password'
   ```

4. Deploy the Lambda function:
   ```bash
   mkdir lambda/package
   pip install -r lambda/requirements.txt -t lambda/package
   cp lambda/lambda_function.py lambda/package/
   cd lambda/package/
   zip -r ../lambda_function.zip .
   aws lambda create-function \
       --function-name GBFSDataFetcher \
       --runtime python3.9 \
       --role <Your Lambda Role ARN> \
       --handler lambda_function.lambda_handler \
       --zip-file fileb://lambda_function.zip \
       --environment Variables={rds_password=your_rds_password,providers='your provider list i.e: [
        {"name": "Careem", "url": "https://dubai.publicbikesystem.net/customer/gbfs/v2/gbfs.json"},
        {"name": "Nextbike", "url": "https://api.nextbike.net/maps/gbfs/v1/nextbike_ae/gbfs.json"},
        {"name": "CitiBike", "url": "https://gbfs.citibikenyc.com/gbfs/gbfs.json"}]'}
   ```
