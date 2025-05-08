# Project Title: ADK API

## Description
ADK API is a Python-based application that provides an API for querying information using a search agent. It is built with FastAPI, allowing for high-performance asynchronous requests.

## Project Structure
```
adk-api
├── src
│   ├── api
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routes
│   │       ├── __init__.py
│   │       └── query.py
│   ├── agent
│   │   ├── __init__.py
│   │   └── search_agent.py
│   ├── config
│   │   ├── __init__.py
│   │   └── settings.py
│   └── utils
│       ├── __init__.py
│       └── logging.py
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── requirements.txt
├── setup.py
└── README.md
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd adk-api
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
To run the API, execute the following command:
```
uvicorn src.api.main:app --reload
```
This will start the FastAPI application, and you can access the API at `http://127.0.0.1:8000`.

## API Endpoints
- **GET /query**: Endpoint for querying information using the search agent.

## Testing
To run the tests, use the following command:
```
pytest
```

## Environment Variables
Create a `.env` file in the root directory and add the necessary environment variables as specified in `.env.example`.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.# bobadk
