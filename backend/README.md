# PriceMatch AI Backend

FastAPI backend for PriceMatch AI fashion discovery app.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

4. Update `.env` with your API keys and configuration.

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

API documentation: `http://localhost:8000/docs`

## Environment Variables

See `.env.example` for required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `GOOGLE_GEMINI_API_KEY`: Google Gemini API key
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: AWS credentials for S3
- `AWS_S3_BUCKET`: S3 bucket name for image storage

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/apple` - Apple Sign-In
- `GET /api/auth/me` - Get current user

### Visual Search
- `POST /api/search/image` - Upload image and search
- `GET /api/search/history` - Get search history
- `GET /api/search/{id}` - Get specific search

### Favorites
- `POST /api/favorites` - Add to favorites
- `DELETE /api/favorites/{product_id}` - Remove from favorites
- `GET /api/favorites` - Get all favorites

### Recommendations
- `GET /api/recommendations` - Get personalized recommendations
- `POST /api/recommendations/track` - Track interaction

### Subscription
- `GET /api/subscription/status` - Get subscription status
- `GET /api/subscription/usage` - Get usage stats
- `POST /api/subscription/webhook` - Apple webhook handler

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
alembic upgrade head
```

## Production Deployment

1. Set up PostgreSQL database
2. Configure environment variables
3. Set up AWS S3 bucket for images
4. Deploy to Railway, Render, or Google Cloud Run
5. Configure domain and SSL
6. Set up monitoring (Sentry)

## Notes

- Free tier: 5 searches/day
- Premium: Unlimited searches
- Images are stored in S3
- Mock product data for MVP (replace with real APIs)
