pipeline {
    agent any
    
    environment {
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'
        DOCKER_COMPOSE_DIR = './'  // Directory where docker-compose.yml is located
    }
    
    stages {
        stage('Checkout') {
            steps {
                // Checkout the source code from GitHub
                git branch: 'main', url: 'https://github.com/winterwolfx2h/itshield.git'
            }
        }
        
        stage('Build') {
            steps {
                script {
                    // Build Docker images and containers using Docker Compose
                    echo 'Building Docker images and containers'
                    sh '''
                    cd ${DOCKER_COMPOSE_DIR}
                    docker-compose down  # Stop any existing containers
                    docker-compose up -d  # Build and start containers in detached mode
                    '''
                }
            }
        }
        
        stage('Test') {
            steps {
                script {
                    // You can add tests here if needed, e.g., running unit tests or integration tests.
                    echo 'Running tests...'
                    // Example: sh './run_tests.sh'
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    // Deploy the app or do other post-deployment steps
                    echo 'Deploying app to production'
                    // Example: sh './deploy.sh'
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                script {
                    // Clean up any resources if necessary, like stopping containers
                    echo 'Cleaning up'
                    sh '''
                    cd ${DOCKER_COMPOSE_DIR}
                    docker-compose down
                    '''
                }
            }
        }
    }

    post {
        always {
            // Clean up or archive test results if needed
            echo 'Cleaning up'
            sh 'docker-compose down'
        }

        success {
            echo 'Build and Deployment Successful!'
        }

        failure {
            echo 'Build or Deployment Failed!'
        }
    }
}

