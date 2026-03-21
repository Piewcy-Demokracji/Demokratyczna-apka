# Voting App

A web application for creating and voting on polls with Angular frontend and FastAPI backend.

## Project Structure

```
.
├── project/                    # Backend (FastAPI)
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   └── polls.py       # Poll endpoints
│   │   ├── core/              # Core functionality
│   │   │   ├── security.py    # JWT and password hashing
│   │   │   └── database.py    # Database configuration
│   │   ├── models/            # Database models
│   │   │   └── user.py        # User, Poll, PollOption, Vote models
│   │   └── schemas/           # Pydantic schemas
│   │       ├── user.py        # User schemas
│   │       └── poll.py        # Poll schemas
│   └── main.py                # FastAPI application
├── frontend/                  # Frontend (Angular)
│   ├── src/
│   │   ├── app/
│   │   │   ├── features/
│   │   │   │   ├── auth/      # Authentication components
│   │   │   │   │   ├── login.component.ts
│   │   │   │   │   ├── login.component.html
│   │   │   │   │   ├── register.component.ts
│   │   │   │   │   └── register.component.html
│   │   │   │   └── home/      # Home page
│   │   │   │       ├── home.component.ts
│   │   │   │       └── home.component.html
│   │   │   ├── core/
│   │   │   │   ├── services/
│   │   │   │   │   ├── auth.service.ts
│   │   │   │   │   └── poll.service.ts
│   │   │   │   └── auth.interceptor.ts
│   │   │   ├── app.module.ts
│   │   │   ├── app-routing.module.ts
│   │   │   └── app.component.ts
│   │   ├── main.ts
│   │   └── index.html
│   ├── package.json
│   └── angular.json
└── requirements.txt           # Python dependencies

```

## Features

- ✅ User authentication (login/register)
- ✅ JWT-based security
- ✅ Responsive home page
- 🔄 Create polls (in development)
- 🔄 Vote on polls (in development)
- 🔄 View poll results (in development)

## Getting Started

### Backend Setup (FastAPI)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   cd project
   uvicorn main:app --reload
   ```
   
   The API will be available at `http://localhost:8000`
   API documentation: `http://localhost:8000/docs`

### Frontend Setup (Angular)

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run the development server:
   ```bash
   npm start
   ```
   
   The application will be available at `http://localhost:4200`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user

### Polls
- `GET /api/polls/` - Get all polls (coming soon)
- `POST /api/polls/` - Create a new poll (coming soon)
- `GET /api/polls/{poll_id}` - Get a specific poll (coming soon)
- `POST /api/polls/{poll_id}/vote` - Vote on a poll (coming soon)

## Next Steps

1. Implement full poll CRUD operations
2. Implement voting functionality
3. Add real-time poll results
4. Add user profile management
5. Add poll categories/tags
6. Implement poll search and filtering
7. Add admin panel
8. Deployment configuration

## Tech Stack

**Backend:**
- FastAPI
- SQLAlchemy
- JWT (python-jose)
- Passlib & bcrypt

**Frontend:**
- Angular 17
- TypeScript
- RxJS

## License

MIT
