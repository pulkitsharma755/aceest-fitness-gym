// ---------------------------------------------------------------------
// ACEest Fitness & Gym - Jenkins BUILD pipeline (Windows agent)
//
// Jenkins is the second validation layer: it pulls the latest code from
// GitHub and performs a clean build in a controlled environment, so a
// build that only worked because of something on a developer laptop
// fails here.
//
// This variant uses `bat` steps because the Jenkins controller runs as a
// Windows service and has no Unix shell. The logic is identical to the
// Linux version kept alongside it in Jenkinsfile.linux: checkout, clean
// environment, lint, build check, test, optional Docker image.
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
        // If Jenkins cannot find Python, replace with the full path, e.g.
        PYTHON = 'C:\\Users\\Pulkit\\AppData\\Local\\Programs\\Python\\Python314\\python.exe'
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
                bat 'git rev-parse --short HEAD'
            }
        }

        stage('Clean Build Environment') {
            steps {
                echo 'Creating a fresh virtual environment...'
                bat """
                    if exist %VENV% rmdir /s /q %VENV%
                    %PYTHON% -m venv %VENV%
                    call %VENV%\\Scripts\\activate.bat
                    python -m pip install --upgrade pip
                    pip install -r requirements-dev.txt
                """
            }
        }

        stage('Lint') {
            steps {
                echo 'Checking for syntax errors and style violations...'
                bat """
                    call %VENV%\\Scripts\\activate.bat
                    flake8 . --count --statistics
                """
            }
        }

        stage('Build Check') {
            steps {
                echo 'Confirming the application builds and imports...'
                bat """
                    call %VENV%\\Scripts\\activate.bat
                    python -c "from aceest import create_app; create_app(db_path=':memory:'); print('Application build OK')"
                """
            }
        }

        stage('Unit Tests') {
            steps {
                echo 'Running the Pytest suite...'
                bat """
                    call %VENV%\\Scripts\\activate.bat
                    pytest -v --junitxml=report.xml --cov=aceest --cov-report=xml
                """
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'report.xml'
                }
            }
        }

        stage('Docker Image') {
            // Skipped automatically where the agent has no Docker daemon.
            when {
                expression { bat(script: 'where docker', returnStatus: true) == 0 }
            }
            steps {
                echo 'Building the Docker image...'
                bat """
                    docker build --target runtime -t %IMAGE_NAME%:%BUILD_NUMBER% .
                    docker tag %IMAGE_NAME%:%BUILD_NUMBER% %IMAGE_NAME%:latest
                    docker images %IMAGE_NAME%
                """
            }
        }
    }

    post {
        success {
            echo "BUILD SUCCESS - build #${env.BUILD_NUMBER}"
        }
        failure {
            echo 'BUILD FAILED - check the console output for the failing stage'
        }
        always {
            echo 'Cleaning the workspace...'
            bat 'if exist %VENV% rmdir /s /q %VENV%'
        }
    }
}
