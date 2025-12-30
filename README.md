# Renttrix

Renttrix is a property management system designed to simplify the management of rental properties. It provides landlords and property managers with tools to track tenants, manage payments, and oversee property-related tasks efficiently. The system includes features such as tenant dashboards, payment tracking, and room management, all accessible through an intuitive web interface.

## Features
- Tenant and landlord dashboards
- Payment tracking and receipt management
- Room and property management
- Tenant onboarding and archiving
- Integration with Django admin for advanced management

## Prerequisites
Before running Renttrix on your local machine, ensure you have the following installed:
- Python 3.8+
- pip (Python package manager)
- Git
- SQLite (or any other database supported by Django)
- Docker (optional, for containerized deployment)

## Installation
Follow these steps to set up Renttrix on your localhost:

1. **Clone the Repository**
   ```bash
   git clone https://github.com/benjaminparinas-tech/RENTTRIX.git
   cd RENTTRIX
   ```

2. **Set Up a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations**
   ```bash
   python manage.py migrate
   ```

5. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```

6. **Access the Application**
   Open your browser and navigate to `http://127.0.0.1:8000`.

## Optional: Using Docker
If you prefer to use Docker, follow these steps:

1. **Build the Docker Image**
   ```bash
   docker build -t renttrix .
   ```

2. **Run the Docker Container**
   ```bash
   docker run -p 8000:8000 renttrix
   ```

3. **Access the Application**
   Open your browser and navigate to `http://127.0.0.1:8000`.

## Contributing
Contributions are welcome! If you'd like to contribute to Renttrix, please fork the repository and submit a pull request.