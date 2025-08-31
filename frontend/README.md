# Daily Challenge Frontend

This is a simple React frontend for the Daily Challenge API. It demonstrates the basic functionality of the API and allows users to interact with the various endpoints.

## Features

- User authentication (login and registration)
- Tag management (create, view, update, delete)
- User profile management
- Dashboard view

## Setup

1. **Install dependencies**

```bash
cd frontend
npm install
```

2. **Start the development server**

```bash
npm run dev
```

3. **Connect to the API**

The frontend is configured to connect to the FastAPI backend at `http://localhost:8000/api`. Make sure the backend is running on this address.

## API Integration

The frontend interacts with these API endpoints:

- **Authentication**:
  - `POST /api/auth/register` - Register a new user
  - `POST /api/auth/login` - Login with email and password
  - `GET /api/auth/me` - Get current user profile

- **Tags**:
  - `GET /api/tags` - Get all tags with optional filtering
  - `GET /api/tags/{id}` - Get a specific tag by ID
  - `POST /api/tags` - Create a new tag
  - `PUT /api/tags/{id}` - Update an existing tag
  - `DELETE /api/tags/{id}` - Delete a tag

- **Users**:
  - `GET /api/users` - Get all users (admin only)
  - `GET /api/users/{id}` - Get a specific user by ID (admin only)

## Technologies Used

- React
- React Router
- Axios for API communication
- Vite for build and development

## Development

This is a simple demonstration frontend. For production use, you should add:

1. Form validation
2. Error handling
3. Loading indicators
4. Token refresh logic
5. Better state management (e.g., using Redux or Context API)
6. Unit and integration tests
