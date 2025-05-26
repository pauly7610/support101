#!/bin/bash

# Clean up Python and Node environments
echo "Cleaning Python and Node environments..."
rm -rf venv .venv __pycache__ .pytest_cache
find . -name "*.pyc" -delete

# Set up Python virtual environment and install dependencies (from app/backend)
echo "Setting up Python virtual environment and installing dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r app/backend/requirements.txt
pip show PyJWT || pip install PyJWT

# Clean and install Node.js dependencies in each app
echo "Cleaning and installing Node.js dependencies..."
for dir in apps/*; do
  if [ -f "$dir/package.json" ]; then
    cd $dir
    rm -rf node_modules
    rm -f package-lock.json yarn.lock
    npm install
    cd ../..
  fi
done

# Run backend tests (from app/backend)
echo "Running backend tests..."
cd app/backend
pytest || echo "Backend tests failed. Review errors above."
cd ../..

# Run frontend tests in each app
echo "Running frontend tests..."
for dir in apps/*; do
  if [ -f "$dir/package.json" ]; then
    cd $dir
    npm test || echo "Frontend tests failed in $dir. Review errors above."
    cd ../..
  fi
done

# Lint Python code (from app/backend)
echo "Linting Python code..."
cd app/backend
flake8 .
cd ../..

# Lint JS/TS code in each app
echo "Linting JavaScript/TypeScript code..."
for dir in apps/*; do
  if [ -f "$dir/package.json" ]; then
    cd $dir
    npm run lint || echo "Linting failed in $dir."
    cd ../..
  fi
done

echo "All done! Please review any errors above and address as needed."
