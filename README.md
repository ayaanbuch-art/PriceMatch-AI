# PriceMatch AI - Complete MVP Codebase

AI-powered fashion discovery app that helps users find cheaper alternatives to clothing and shoes through visual search.

## 🎯 What's Included

### ✅ Backend (FastAPI + Python)
- **Authentication**: Email/password + Apple Sign-In support
- **Visual Search**: Google Gemini Vision integration for detailed clothing analysis
- **Product Matching**: Search and similarity scoring (currently mock data)
- **Favorites**: Save products
- **Recommendations**: Personalized product feed based on user history
- **Subscriptions**: Apple IAP webhook handling
- **Usage Limits**: Free tier (5 searches/day) vs Premium (unlimited)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Image Storage**: AWS S3 integration

### ✅ iOS App (SwiftUI)
- **Authentication UI**: Login/Register with email/password
- **Camera Integration**: Take photos or choose from library
- **Visual Search**: Upload images and get AI analysis
- **Product Grid**: Depop-style cards with similarity percentages
- **Recommendations Feed**: Personalized "For You" tab
- **Profile**: Subscription status, favorites, search history
- **Usage Tracking**: Shows remaining free searches
- **Networking**: Complete API service with JWT authentication

## 🚀 Complete Setup Guide

### Prerequisites

Before starting, make sure you have:
- **Python 3.11+** installed ([Download here](https://www.python.org/downloads/))
- **PostgreSQL** installed ([Download here](https://www.postgresql.org/download/))
- **Xcode 15+** installed (from Mac App Store)
- **macOS** for iOS development
- **Git** installed (usually comes with macOS)

### Part 1: Backend Setup (Detailed)

#### Step 1: Navigate to Backend Directory
Open Terminal and go to the project:
```bash
cd "Desktop/Desktop - Ayaan's MacBook Air/PriceMatch AI/backend"
```

#### Step 2: Create Python Virtual Environment
This isolates your project dependencies:
```bash
python3 -m venv venv
```

**What this does:** Creates a folder called `venv` with an isolated Python environment.

#### Step 3: Activate Virtual Environment
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

**You should see** `(venv)` appear at the start of your terminal prompt. This means it worked!

#### Step 4: Install Python Dependencies
```bash
pip install -r requirements.txt
```

**This will install:** FastAPI, SQLAlchemy, Google Gemini SDK, AWS SDK, and all other dependencies.

**Expected time:** 1-2 minutes

**If you get errors**, try:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Set Up PostgreSQL Database

**Option A: Local PostgreSQL (Recommended for testing)**

1. Install PostgreSQL (if not already installed):
   - Mac: `brew install postgresql` (if you have Homebrew)
   - Or download from https://www.postgresql.org/download/

2. Start PostgreSQL:
   ```bash
   brew services start postgresql
   # Or on Linux: sudo systemctl start postgresql
   ```

3. Create a database:
   ```bash
   createdb pricematch
   ```

   **If you get "command not found":**
   ```bash
   /usr/local/bin/createdb pricematch
   ```

4. Your database URL will be:
   ```
   postgresql://your_username@localhost:5432/pricematch
   ```

   Replace `your_username` with your Mac username (type `whoami` in terminal to find it).

**Option B: Use Supabase (Easier, cloud-based)**

1. Go to https://supabase.com and create free account
2. Create a new project
3. Go to Project Settings → Database
4. Copy the "Connection String" (URI format)
5. Use this as your DATABASE_URL

#### Step 6: Set Up Environment Variables

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in a text editor:
   ```bash
   open .env
   # Or use: nano .env
   ```

3. Fill in the required values:

```env
# Database - REQUIRED
DATABASE_URL=postgresql://your_username@localhost:5432/pricematch

# JWT Secret - REQUIRED (change to something random)
SECRET_KEY=your-super-secret-key-change-this-to-something-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Google Gemini API - REQUIRED
GOOGLE_GEMINI_API_KEY=your-gemini-api-key-here

# AWS S3 - REQUIRED
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=pricematch-images
AWS_REGION=us-east-1

# Google Shopping API (optional for now)
GOOGLE_SHOPPING_API_KEY=

# Affiliate Networks (optional for now)
AMAZON_ASSOCIATE_TAG=
AMAZON_ACCESS_KEY=
AMAZON_SECRET_KEY=

# App Configuration
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]

# Apple App Store (optional for now)
APPLE_BUNDLE_ID=com.pricematch.app
APPLE_SHARED_SECRET=
```

#### Step 7: Get Required API Keys

**A. Google Gemini API Key (REQUIRED)**

1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste it in `.env` as `GOOGLE_GEMINI_API_KEY`

**B. AWS S3 Setup (REQUIRED)**

1. Go to https://aws.amazon.com and create account (free tier available)
2. Go to S3 service
3. Click "Create bucket"
   - Bucket name: `pricematch-images` (or any unique name)
   - Region: `us-east-1` (or your preferred region)
   - Uncheck "Block all public access" (we need public read for images)
   - Create bucket

4. Get AWS credentials:
   - Go to IAM → Users → Create User
   - Give S3 permissions
   - Create access key
   - Copy Access Key ID and Secret Access Key
   - Add to `.env`

5. Update bucket name in `.env`:
   ```env
   AWS_S3_BUCKET=your-actual-bucket-name
   AWS_REGION=us-east-1
   ```

#### Step 8: Create Database Tables

The app will create tables automatically on first run, but you can also use Alembic:

```bash
# Install alembic if needed
pip install alembic

# Initialize (only first time)
alembic init migrations

# Create and run migrations
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head
```

**Or just run the server** and it will create tables automatically!

#### Step 9: Run the Backend Server

```bash
uvicorn app.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**If it works, you should see:**
- Server running at http://localhost:8000
- API documentation at http://localhost:8000/docs

#### Step 10: Test the Backend

Open your browser and go to:
```
http://localhost:8000/docs
```

You should see the FastAPI Swagger documentation with all API endpoints!

Try the health check:
```
http://localhost:8000/health
```

Should return: `{"status": "healthy"}`

**Common Backend Errors & Fixes:**

**Error: "No module named 'app'"**
- Make sure you're in the `backend` directory
- Make sure virtual environment is activated (you see `(venv)`)

**Error: "connection refused" (database)**
- PostgreSQL is not running: `brew services start postgresql`
- Wrong DATABASE_URL in `.env`

**Error: "ImportError: No module named 'google.generativeai'"**
- Install dependencies again: `pip install -r requirements.txt`

**Error: "Invalid API key" (Gemini)**
- Check your Google Gemini API key in `.env`
- Make sure there are no extra spaces

---

### Part 2: iOS Setup (Detailed)

#### Step 1: Open Terminal and Navigate to iOS Folder
```bash
cd "Desktop/Desktop - Ayaan's MacBook Air/PriceMatch AI/iOS"
```

#### Step 2: Open Project in Xcode

**Method 1: Command line**
```bash
open SnapStyleAI.xcodeproj
```

**Method 2: Finder**
- Open Finder
- Navigate to the iOS folder
- Double-click `SnapStyleAI.xcodeproj`

Xcode should open!

#### Step 3: Configure Xcode Project

**A. Select Your Team (for code signing)**
1. In Xcode, click on the project name in the left sidebar (blue icon)
2. Click on "SnapStyleAI" target
3. Go to "Signing & Capabilities" tab
4. Check "Automatically manage signing"
5. Select your Team (your Apple ID)
   - If you don't have a team, click "Add Account" and sign in with your Apple ID
   - Free accounts work fine for testing!

**B. Change Bundle Identifier**
1. Still in "Signing & Capabilities"
2. Change Bundle Identifier to something unique:
   ```
   com.yourname.pricematchai
   ```

#### Step 4: Update API Base URL

1. In Xcode, open: `Services/APIService.swift`
2. Find this line (near the top):
   ```swift
   private let baseURL = "http://localhost:8000"
   ```

3. **If running on simulator**: Keep as is
4. **If running on physical device**: Change to your computer's IP address:
   ```swift
   private let baseURL = "http://192.168.1.XXX:8000"
   ```

**To find your IP address:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Or: System Preferences → Network → Your connection → look for "IP Address"

#### Step 5: Add Privacy Permissions

1. In Xcode, find and open `Info.plist`
2. Right-click in the file → Add Row
3. Add these keys:

**NSCameraUsageDescription**
- Type: String
- Value: `We need camera access to take photos of clothing for search`

**NSPhotoLibraryUsageDescription**
- Type: String
- Value: `We need photo library access to select images for search`

#### Step 6: Select Simulator or Device

At the top of Xcode, you'll see a device selector:
```
SnapStyleAI > iPhone 15 Pro
```

Click it to choose:
- **Simulator**: Select any iPhone model (iPhone 15 Pro recommended)
- **Physical Device**: Connect your iPhone via USB and select it

**Note:** Camera only works on physical devices! Simulator will show camera button but can't actually take photos.

#### Step 7: Build and Run

Press `Cmd + R` or click the Play button (▶️) in top left

**First build takes longer** (1-2 minutes) - this is normal!

**Expected result:**
- App launches in simulator or on your device
- You see the login/signup screen
- You can create an account and log in

#### Step 8: Test the App

1. **Create Account:**
   - Click "Sign Up"
   - Enter email and password
   - Tap "Sign Up"
   - You should be logged in!

2. **Test Search:**
   - Go to Search tab (camera icon)
   - Click "Choose from Library" (simulator) or "Take Photo" (device)
   - Select/take a photo of clothing
   - Wait for AI analysis (5-10 seconds)
   - See results with product matches!

3. **Check Recommendations:**
   - Go to "For You" tab
   - See personalized recommendations

4. **View Profile:**
   - Go to Profile tab
   - See your account info and subscription status

**Common iOS Errors & Fixes:**

**Error: "Code signing failed"**
- Make sure you selected your Team in Signing & Capabilities
- Try changing Bundle Identifier to something unique

**Error: "Could not connect to development server"**
- Backend is not running (go back to Terminal, start backend)
- Wrong baseURL in APIService.swift
- If using physical device, use your computer's IP address, not localhost

**Error: "Camera not available"**
- You're using simulator (camera only works on real devices)
- Or: You denied camera permission (go to Settings → Privacy → Camera)

**Error: Build failed with "Missing module"**
- Clean build folder: Cmd + Shift + K
- Build again: Cmd + R

**Error: "Failed to verify credentials"**
- Backend is not running
- Wrong API URL
- Check backend terminal for errors

---

### Part 3: Testing the Complete Flow

#### 1. Start Backend (Terminal 1)
```bash
cd "Desktop/Desktop - Ayaan's MacBook Air/PriceMatch AI/backend"
source venv/bin/activate
uvicorn app.main:app --reload
```

Keep this terminal open!

#### 2. Run iOS App (Xcode)
- Open Xcode project
- Press Cmd + R
- Wait for app to launch

#### 3. Test Complete User Flow

**Step-by-step test:**
1. ✅ Register a new account
2. ✅ Should automatically log you in
3. ✅ See the Search screen with camera button
4. ✅ Click "Choose from Library"
5. ✅ Select a photo of clothing
6. ✅ Wait 5-10 seconds for AI analysis
7. ✅ See detailed analysis (style, colors, description)
8. ✅ See grid of similar products with similarity %
9. ✅ Go to "For You" tab
10. ✅ See personalized recommendations
11. ✅ Go to Profile tab
12. ✅ See subscription status (Free - 4/5 searches remaining)

**If everything works: Congratulations! 🎉**

---

### Part 4: What to Do Next

#### For Local Development Testing
You can now:
- Test with different clothing images
- Create multiple accounts
- Test the recommendations
- Explore the API at http://localhost:8000/docs

#### Before Production
You need to:
1. **Replace mock products** with real Google Shopping API
2. **Add real affiliate links** (sign up for Amazon Associates, etc.)
3. **Deploy backend** to a cloud service (Railway, Render, Heroku)
4. **Update iOS app** with production API URL
5. **Implement subscription payments** with StoreKit
6. **Test on TestFlight**
7. **Submit to App Store**

See the "To-Do for Production" section below for details!

---

### Quick Reference Commands

**Backend:**
```bash
# Activate environment
source venv/bin/activate

# Run server
uvicorn app.main:app --reload

# View logs
# Just watch the terminal!

# Stop server
Ctrl + C
```

**iOS:**
```bash
# Open project
cd iOS
open SnapStyleAI.xcodeproj

# In Xcode:
# Build: Cmd + B
# Run: Cmd + R
# Stop: Cmd + .
# Clean: Cmd + Shift + K
```

**Check if backend is running:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

---

### 🔧 Comprehensive Troubleshooting Guide

#### Backend Issues

**Problem: "ModuleNotFoundError: No module named 'fastapi'"**
```bash
# Solution:
pip install -r requirements.txt
# Or if that doesn't work:
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib google-generativeai
```

**Problem: "Could not connect to database"**
```bash
# Check if PostgreSQL is running:
brew services list | grep postgresql

# If not running:
brew services start postgresql

# Or start manually:
pg_ctl -D /usr/local/var/postgres start
```

**Problem: "Table does not exist"**
```bash
# The app should create tables automatically, but if not:
# In Python shell (with venv activated):
python
>>> from app.database import engine, Base
>>> from app.models import *
>>> Base.metadata.create_all(bind=engine)
>>> exit()
```

**Problem: "Invalid Gemini API key"**
- Double-check your API key at https://makersuite.google.com/app/apikey
- Make sure there are no spaces or quotes around the key in `.env`
- Try regenerating the key

**Problem: "S3 Access Denied"**
```bash
# Check your AWS credentials:
# 1. Go to AWS IAM console
# 2. Find your user
# 3. Make sure it has S3 permissions
# 4. Regenerate access keys if needed
```

**Problem: "Address already in use (port 8000)"**
```bash
# Another process is using port 8000
# Find and kill it:
lsof -ti:8000 | xargs kill -9

# Or use a different port:
uvicorn app.main:app --reload --port 8001
# (Then update iOS app's baseURL too!)
```

#### iOS Issues

**Problem: "Development Team not found"**
- Go to Xcode → Preferences → Accounts
- Click "+" and add your Apple ID
- Go back to project → Signing & Capabilities
- Select your team

**Problem: "Failed to register bundle identifier"**
- Bundle ID is already taken
- Change it to something unique: `com.yourname.pricematch.unique123`

**Problem: "Unable to install app"**
- Clean build folder: Cmd + Shift + K
- Delete app from simulator/device
- Build and run again

**Problem: "API calls failing with 'Connection refused'"**

On **Simulator**:
```swift
// In APIService.swift, use:
private let baseURL = "http://localhost:8000"
```

On **Physical Device**:
```swift
// In APIService.swift, use your computer's IP:
private let baseURL = "http://192.168.1.XXX:8000"

// Find your IP with:
// Terminal: ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Problem: "Cannot take photos in simulator"**
- Camera only works on physical devices!
- Use "Choose from Library" in simulator
- Or test on real iPhone/iPad

**Problem: "App crashes on launch"**
- Check Xcode console for error messages
- Make sure backend is running
- Check that KeychainHelper isn't causing issues
- Try: Product → Clean Build Folder (Cmd + Shift + K)

#### Google Gemini API Issues

**Problem: "Quota exceeded"**
- You've hit the free tier limit
- Wait 1 minute (free tier has rate limits)
- Or upgrade to paid plan

**Problem: "Invalid image"**
- Image file is corrupted
- Image is too large (max 20MB)
- Try compressing the image first

**Problem: "Response parsing error"**
- Gemini returned non-JSON response
- Check the backend logs for the actual response
- The prompt might need adjustment

#### Database Issues

**Problem: "Could not create database"**
```bash
# Make sure PostgreSQL is installed:
postgres --version

# If not installed on Mac:
brew install postgresql

# On Linux:
sudo apt-get install postgresql
```

**Problem: "Permission denied for database"**
```bash
# Check your PostgreSQL user permissions:
psql postgres
postgres=# \du  # List users and their permissions
postgres=# ALTER USER your_username CREATEDB;
postgres=# \q
```

**Problem: "Database encoding error"**
```bash
# When creating database, specify UTF-8:
createdb -E UTF8 pricematch
```

---

### 📸 What You Should See

#### Backend Terminal (When Running)
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### API Documentation (http://localhost:8000/docs)
You should see:
- Green "Authorize" button at top
- Sections: authentication, search, favorites, recommendations, subscription
- Expandable endpoints with "Try it out" buttons

#### iOS App Screens

**1. Login Screen:**
- "PriceMatch AI" title
- "Find cheaper alternatives instantly" subtitle
- Email and password fields
- Login/Sign Up toggle

**2. Search Screen (Empty State):**
- Camera icon
- "Take a photo of any clothing or shoes" text
- "X searches remaining today" badge (for free users)
- "Take Photo" button (blue)
- "Choose from Library" button

**3. Search Results:**
- Original photo at top
- "AI Analysis" section with detailed description
- Color tags
- Price estimate
- "Similar Items" grid (2 columns)
- Product cards showing:
  - Product image
  - Similarity % badge (green)
  - Product title
  - Merchant name
  - Price (blue) and original price (strikethrough)

**4. For You Tab:**
- Grid of recommended products
- Same card style as search results

**5. Profile:**
- User icon and email
- Subscription section (Free Tier or Premium)
- Search usage indicator
- Favorites, Search History, Settings links
- Log Out button (red)

---

### 🎯 Expected Behavior

#### First Time Running

**Backend:**
1. First run creates all database tables
2. You'll see SQL statements in the terminal (if DEBUG=true)
3. Server starts and listens on port 8000

**iOS:**
1. First build takes 1-2 minutes (compiling everything)
2. App launches to login screen
3. No saved login (fresh start)

#### Visual Search Flow

1. **User taps "Choose from Library"** → Image picker opens
2. **User selects clothing image** → Image picker closes
3. **App shows loading indicator** → Wait 5-10 seconds
4. **AI Analysis happens on backend:**
   - Image uploaded to S3
   - Google Gemini analyzes image
   - Product search runs
   - Results saved to database
5. **Results appear** → Shows analysis + products

**Backend logs you'll see:**
```
INFO: POST /api/search/image - 200 OK (8.5s)
```

#### Free Tier Limits

- User gets 5 searches per day
- On 6th search: Gets error "Daily limit reached"
- Counter resets at midnight
- Premium users: Unlimited searches

---

### 💡 Development Tips

#### Backend Development

**Hot Reload:**
- Backend automatically reloads when you save Python files
- No need to restart the server!

**View Database:**
```bash
# Connect to PostgreSQL:
psql pricematch

# List tables:
\dt

# View users:
SELECT * FROM users;

# View searches:
SELECT id, user_id, created_at FROM search_history;

# Exit:
\q
```

**Test API Endpoints:**
```bash
# Health check:
curl http://localhost:8000/health

# Register user:
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# The response includes an access_token - copy it!

# Get current user:
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### iOS Development

**View Console Logs:**
- In Xcode, show Debug Area: Cmd + Shift + Y
- See print statements and errors

**Debug API Calls:**
Add prints in APIService.swift:
```swift
func get<T: Decodable>(_ path: String) async throws -> T {
    print("📡 API GET: \(baseURL)\(path)")
    // ... rest of code
}
```

**Reset App Data:**
- Delete app from simulator
- Or: Product → Clean Build Folder (Cmd + Shift + K)
- Keychain data persists until you delete the app

**Test on Multiple Devices:**
- Use different simulators: iPhone SE, iPhone 15 Pro Max
- Test on real device for camera functionality

---

### 🚢 Ready to Deploy?

Once everything works locally, see the production deployment guide in the "To-Do for Production" section!

Quick checklist before deploying:
- [ ] Backend works locally
- [ ] iOS app works on simulator and device
- [ ] Database is set up
- [ ] All API keys are working
- [ ] You've tested the complete user flow
- [ ] You have real product API integrated (or mock data is acceptable for beta)
- [ ] Ready to deploy backend to cloud service
- [ ] Ready to submit iOS app to TestFlight

## 📋 Environment Variables

### Required Backend Variables

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/pricematch

# JWT Secret
SECRET_KEY=your-secret-key-change-in-production

# Google Gemini API (REQUIRED)
GOOGLE_GEMINI_API_KEY=your-gemini-api-key

# AWS S3 (REQUIRED for image uploads)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET=pricematch-images
AWS_REGION=us-east-1

# Apple App Store (for subscriptions)
APPLE_BUNDLE_ID=com.pricematch.app
APPLE_SHARED_SECRET=your-apple-shared-secret
```

## 🎨 MVP Features

### Visual Search with AI
- Take photo of any clothing/shoes
- Get thorough AI analysis (style, material, features, price estimate)
- Find similar products at lower prices
- Similarity percentage for each match
- Detailed product descriptions

### User Accounts
- Email/password registration and login
- Profile management
- Search history
- Favorites

### Recommendations
- Personalized "For You" feed
- Based on search history and interactions
- Learns user preferences over time

### Monetization
- Free tier: 5 searches/day
- Premium tier: Unlimited searches
- Subscription: $3.49/month or $39.99/year
- Affiliate marketing ready

## 📦 Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy
- **AI**: Google Gemini Vision API
- **Storage**: AWS S3
- **Auth**: JWT tokens, Apple Sign-In ready
- **Payments**: Apple IAP webhooks

### iOS
- **Language**: Swift 5.9+
- **UI**: SwiftUI
- **Architecture**: MVVM
- **Min iOS**: 16.0
- **Networking**: URLSession with async/await
- **Security**: Keychain for token storage

## 🔧 What's Mock vs Real

### Currently Mock (Replace for Production)
- **Product Search**: Mock products generated by backend
- **Product Images**: Placeholder images (https://via.placeholder.com)
- **Affiliate Links**: Mock URLs
- **Apple Sign-In**: Client-side only (need server verification)

### Already Real
- Google Gemini Vision API integration
- Image upload to S3
- Authentication (email/password)
- Database persistence
- Search history
- Recommendations algorithm (basic)

## 📝 To-Do for Production

### High Priority
1. **Replace mock product data**:
   - Integrate Google Shopping API
   - Or integrate affiliate network APIs (Amazon, ShareASale, CJ)
   - Get real product images

2. **Affiliate Integration**:
   - Sign up for affiliate networks
   - Implement proper affiliate link generation
   - Add click tracking

3. **Apple IAP**:
   - Configure StoreKit in iOS app
   - Create subscription products in App Store Connect
   - Implement purchase flow
   - Verify receipts on backend

4. **Apple Sign-In**:
   - Implement proper token verification on backend
   - Configure service ID in Apple Developer Portal

### Medium Priority
5. **Deploy Backend**:
   - Set up PostgreSQL database (AWS RDS, Supabase)
   - Deploy to Railway, Render, or Google Cloud Run
   - Configure S3 bucket and permissions
   - Set up monitoring (Sentry)

6. **iOS Polish**:
   - Add loading states everywhere
   - Better error handling
   - Offline mode support
   - Analytics integration (Firebase, Mixpanel)

7. **Testing**:
   - Unit tests for backend
   - UI tests for iOS
   - Integration tests
   - TestFlight beta

### Low Priority
8. **Post-MVP Features**:
   - AI Fashion Chatbot
   - Wardrobe Analyzer
   - Push notifications
   - Share functionality

## 💰 Cost Estimates

### MVP Costs (per month, ~1000 active users)
- Backend hosting: $15-30
- Database (PostgreSQL): $10-20
- S3 storage: $5-10
- Google Gemini API: $30-100 (depends on usage)
- **Total**: ~$60-150/month

### Break-Even
- Need ~20 monthly subscribers ($3.49 × 20 = $69.80 → $48.86 after Apple's 30%)
- Or ~15 annual subscribers
- Plus affiliate commissions

## 🐛 Known Issues

1. Product search returns mock data - needs real API integration
2. Apple Sign-In needs server-side token verification
3. Subscription paywall not implemented in iOS yet
4. No analytics or crash reporting yet
5. Limited error handling in iOS app

## 📚 Documentation

- [Backend API Documentation](backend/README.md)
- [iOS App Documentation](iOS/README.md)
- [Project Plan](antigravity/project_plan.md)
- [Technical Architecture](docs/technical-architecture.md)

## 🎯 Next Steps

1. Get Google Gemini API key from Google Cloud
2. Set up AWS S3 bucket for images
3. Set up PostgreSQL database
4. Run backend locally
5. Run iOS app and test visual search
6. Replace mock product data with real APIs
7. Deploy backend to production
8. Submit iOS app to TestFlight
9. Gather feedback from beta users
10. Launch on App Store!

## 🤝 Contributing

This is a complete MVP codebase ready for development. To contribute:

1. Clone the repository
2. Set up backend and iOS as described above
3. Make changes in a feature branch
4. Test thoroughly
5. Submit pull request

## 📄 License

MIT License - feel free to use this codebase for your project!

## 🙏 Acknowledgments

- Google Gemini Vision for AI analysis
- FastAPI for excellent Python framework
- SwiftUI for modern iOS development

---

**Built as a complete MVP for PriceMatch AI** 🚀

Ready to launch with:
- ✅ Full backend API
- ✅ Complete iOS app
- ✅ AI-powered visual search
- ✅ User authentication
- ✅ Recommendations
- ✅ Monetization ready

**Just add real product APIs and deploy!** 🎉
