# PriceMatch AI - Quick Start Checklist

Follow this checklist to get your app running in under 30 minutes!

## ✅ Pre-Flight Checklist

- [ ] Python 3.11+ installed? Check: `python3 --version`
- [ ] PostgreSQL installed? Check: `postgres --version`
- [ ] Xcode installed? Check: Open from Applications
- [ ] macOS for iOS development? (required)

---

## 🔧 Backend Setup (15 minutes)

### Step 1: Terminal Setup
```bash
# Navigate to backend
cd "Desktop/Desktop - Ayaan's MacBook Air/PriceMatch AI/backend"

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# You should see (venv) in your prompt
```
- [ ] Virtual environment activated

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```
- [ ] All packages installed (takes 1-2 min)

### Step 3: Database Setup
```bash
# Create database
createdb pricematch

# Verify it exists
psql -l | grep pricematch
```
- [ ] Database created

### Step 4: Get API Keys

**Google Gemini (REQUIRED):**
1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

- [ ] Gemini API key obtained

**AWS S3 (REQUIRED):**
1. Go to: https://aws.amazon.com/s3
2. Create bucket (name: `pricematch-images-yourname`)
3. Get access key from IAM console

- [ ] S3 bucket created
- [ ] AWS credentials obtained

### Step 5: Configure Environment
```bash
# Copy example file
cp .env.example .env

# Edit it
nano .env
# or
open .env
```

**Minimum required in .env:**
```env
DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/pricematch
SECRET_KEY=any-random-string-here-make-it-long
GOOGLE_GEMINI_API_KEY=your-actual-gemini-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
```

- [ ] .env file configured

### Step 6: Start Backend
```bash
uvicorn app.main:app --reload
```

**Should see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

- [ ] Backend running without errors

### Step 7: Test Backend
Open browser: http://localhost:8000/docs

- [ ] API documentation loads
- [ ] See all endpoints listed

**Keep this terminal open!**

---

## 📱 iOS Setup (10 minutes)

### Step 1: Open Xcode
```bash
cd "Desktop/Desktop - Ayaan's MacBook Air/PriceMatch AI/iOS"
open SnapStyleAI.xcodeproj
```

- [ ] Xcode opened

### Step 2: Configure Signing
1. Click project name (blue icon) in left sidebar
2. Select "SnapStyleAI" target
3. Go to "Signing & Capabilities" tab
4. Check "Automatically manage signing"
5. Select your Team (add Apple ID if needed)
6. Change Bundle Identifier to: `com.yourname.pricematchai`

- [ ] Code signing configured

### Step 3: Add Privacy Permissions
1. Open `Info.plist`
2. Add these keys (right-click → Add Row):

**NSCameraUsageDescription**
- Value: `We need camera access to take photos of clothing`

**NSPhotoLibraryUsageDescription**
- Value: `We need photo library access to select images`

- [ ] Privacy permissions added

### Step 4: Update API URL (if needed)
1. Open `Services/APIService.swift`
2. Find: `private let baseURL = "http://localhost:8000"`
3. **For simulator:** Leave as is
4. **For physical device:** Change to your Mac's IP address

- [ ] API URL configured

### Step 5: Build and Run
1. Select simulator: iPhone 15 Pro (at top of Xcode)
2. Press Cmd + R (or click Play ▶️ button)
3. Wait for build (1-2 minutes first time)

**Should see:**
- App launches in simulator
- Login/signup screen appears

- [ ] App builds successfully
- [ ] App launches without crashes

---

## 🧪 Testing (5 minutes)

### Test 1: Create Account
1. In the app, click "Sign Up"
2. Enter:
   - Email: `test@example.com`
   - Password: `password123`
   - Full Name: `Test User`
3. Tap "Sign Up"

**Expected:** Automatically logged in, see Search screen

- [ ] Account created successfully

### Test 2: Visual Search
1. Go to Search tab (camera icon)
2. Click "Choose from Library"
3. Select any clothing image
4. Wait 5-10 seconds

**Expected:**
- Loading indicator appears
- Results show up with:
  - AI analysis
  - Grid of similar products
  - Similarity percentages

- [ ] Search works and returns results

**Backend terminal should show:**
```
INFO: POST /api/search/image - 200 OK
```

### Test 3: Recommendations
1. Go to "For You" tab (heart icon)
2. Should see recommended products

- [ ] Recommendations load

### Test 4: Profile
1. Go to Profile tab (person icon)
2. Should see:
   - Your email
   - Subscription status (Free Tier)
   - Search usage (1/5 searches)

- [ ] Profile displays correctly

---

## ✨ Success!

If all checkboxes are checked, you have a **fully working MVP!**

### What You Can Do Now:
- ✅ Take/upload photos of clothing
- ✅ Get AI analysis with Google Gemini
- ✅ See similar product matches
- ✅ Get personalized recommendations
- ✅ Track search usage
- ✅ Save to favorites

### What's Mock (Needs Real APIs):
- ⚠️ Product results are generated mock data
- ⚠️ Product images are placeholders
- ⚠️ Affiliate links are fake

### Next Steps:
1. Keep testing with different images
2. Try creating multiple accounts
3. Test the 5-search free tier limit
4. When ready: Add real product APIs
5. Deploy backend to production
6. Submit iOS app to App Store

---

## 🆘 Quick Fixes

**Backend won't start?**
```bash
# Make sure you're in backend folder
pwd

# Make sure venv is activated
source venv/bin/activate

# Try reinstalling
pip install -r requirements.txt
```

**iOS won't build?**
```
Product → Clean Build Folder (Cmd + Shift + K)
Then: Cmd + R
```

**Can't connect to backend from iOS?**
- Check backend is running (terminal should show it)
- For physical device, use your IP instead of localhost
- Check firewall isn't blocking port 8000

**Database errors?**
```bash
# Restart PostgreSQL
brew services restart postgresql

# Recreate database
dropdb pricematch
createdb pricematch
```

---

## 📚 Full Documentation

For detailed troubleshooting and advanced setup:
- [Complete README](README.md)
- [Backend README](backend/README.md)
- [iOS README](iOS/README.md)
- [Technical Architecture](docs/technical-architecture.md)
- [Project Plan](antigravity/project_plan.md)

---

**🎉 Congratulations! You've successfully set up PriceMatch AI!**

Now start building, testing, and preparing for launch! 🚀
