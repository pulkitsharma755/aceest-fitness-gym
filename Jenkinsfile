// ---------------------------------------------------------------------
// ACEest Fitness & Gym - Jenkins BUILD pipeline
//
// Jenkins is the second validation layer: it pulls the latest code from
// GitHub and performs a clean build in a controlled environment, so a
// build that only worked because of something on a developer laptop
// fails here.
//
// Declarative syntax is used because the flow is linear: checkout,
// build, lint, test, package.
// ---------------------------------------------------------------------

pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        VENV = 'venv'
        IMAGE_NAME = 'aceest-fitness'
    }

    triggers {
        // Poll GitHub every five minutes. Replace with a webhook on a
        // server that is reachable from the internet.
        pollSCM('H/5 * * * *')
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Pulling the latest code from GitHub...'
                checkout scm
                script {
                    env.GIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }
                echo "Building commit ${env.GIT_SHORT}"
            }
        }

        stage('Clean Build Environment') {
            steps {
                echo 'Creating a fresh virtual environment...'
                sh '''
                    rm -rf ${VENV}
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                echo 'Checking for syntax errors and style violations...'
                sh '''
                    . ${VENV}/bin/activate
                    flake8 . --count --statistics
                '''
            }
        }

        stage('Build Check') {
            steps {
                echo 'Confirming the application builds and imports...'
                sh '''
                    . ${VENV}/bin/activate
                    python -c "from aceest import create_app; create_app(db_path=':memory:'); print('Application build OK')"
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo 'Running the Pytest suite...'
                sh '''
                    . ${VENV}/bin/activate
                    pytest -v --junitxml=report.xml --cov=aceest --cov-report=xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'report.xml'
                }
            }
        }

        stage('Docker Image') {
            // Only runs where the Jenkins agent can reach a Docker daemon.
            when {
                expression { sh(script: 'command -v docker', returnStatus: true) == 0 }
            }
            steps {
                echo 'Building the Docker image...'
                sh '''
                    docker build --target runtime -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                    docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest
                    docker images ${IMAGE_NAME}
                '''
            }
        }
    }

    post {
        success {
            echo "BUILD SUCCESS - commit ${env.GIT_SHORT}, build #${env.BUILD_NUMBER}"
        }
        failure {
            echo "BUILD FAILED - check the console output for the failing stage"
        }
        always {
            echo 'Cleaning the workspace...'
            sh 'rm -rf ${VENV} || true'
        }
    }
}
