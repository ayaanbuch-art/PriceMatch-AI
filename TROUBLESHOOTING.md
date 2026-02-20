# PriceMatch AI - Troubleshooting Guide

Common issues and their solutions, organized by category.

## 🔍 Table of Contents
1. [Backend Issues](#backend-issues)
2. [iOS Issues](#ios-issues)
3. [Database Issues](#database-issues)
4. [API Issues](#api-issues)
5. [Deployment Issues](#deployment-issues)

---

## Backend Issues

### Issue: Virtual Environment Not Activating

**Symptoms:**
- `source venv/bin/activate` doesn't work
- Don't see `(venv)` in terminal prompt

**Solutions:**
```bash
# Method 1: Try absolute path
source /Users/YOUR_USERNAME/Desktop/.../backend/venv/bin/activate

# Method 2: Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Method 3: Use Python directly
python3 -m venv venv
. venv/bin/activate
```

---

### Issue: "ModuleNotFoundError" When Running Server

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
# or
No module named 'app'
```

**Solutions:**
```bash
# 1. Make sure venv is activated
source venv/bin/activate

# 2. Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Install specific missing module
pip install fastapi uvicorn sqlalchemy

# 4. Check you're in the backend directory
pwd  # Should show: .../backend
```

---

### Issue: "Port Already in Use"

**Symptoms:**
```
ERROR: [Errno 48] Address already in use
```

**Solutions:**
```bash
# Option 1: Kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Option 2: Use different port
uvicorn app.main:app --reload --port 8001

# Option 3: Find what's using the port
lsof -i :8000
# Then kill that specific process
```

---

### Issue: Database Connection Refused

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
connection refused
```

**Solutions:**
```bash
# 1. Check if PostgreSQL is running
brew services list | grep postgresql
# or
ps aux | grep postgres

# 2. Start PostgreSQL
brew services start postgresql
# or
pg_ctl -D /usr/local/var/postgres start

# 3. Check DATABASE_URL in .env
# Should be: postgresql://USERNAME@localhost:5432/snapstyle

# 4. Test connection manually
psql -d snapstyle
# If this works, PostgreSQL is fine

# 5. Check PostgreSQL logs
tail -f /usr/local/var/log/postgres.log
```

---

### Issue: Google Gemini API Errors

**Error: "Invalid API Key"**
```bash
# 1. Verify key at https://makersuite.google.com/app/apikey
# 2. Check .env file - no quotes, no spaces:
GOOGLE_GEMINI_API_KEY=AIzaSyAbc123...

# 3. Regenerate API key if needed
# 4. Restart backend server after changing .env
```

**Error: "Quota Exceeded"**
```
Solution:
- Free tier has rate limits (60 requests/minute)
- Wait 1 minute and try again
- Or upgrade to paid plan
- Implement caching to reduce calls
```

**Error: "Invalid Image"**
```bash
# Image is too large or corrupted
# Backend compresses images before sending to Gemini
# Check backend logs for specific error

# Test image processing:
python3
>>> from PIL import Image
>>> img = Image.open("test.jpg")
>>> img.size  # Should return dimensions
```

---

### Issue: AWS S3 Upload Failures

**Error: "Access Denied"**
```bash
# 1. Check AWS credentials in .env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# 2. Verify S3 bucket exists
aws s3 ls s3://your-bucket-name

# 3. Check bucket permissions (must allow public read)
# Go to S3 Console → Bucket → Permissions
# Uncheck "Block all public access"

# 4. Check IAM user permissions
# User needs: s3:PutObject, s3:GetObject, s3:DeleteObject
```

**Error: "Bucket Not Found"**
```bash
# 1. Verify bucket name in .env matches actual bucket
AWS_S3_BUCKET=your-actual-bucket-name

# 2. Check region
AWS_REGION=us-east-1  # Must match bucket region

# 3. Create bucket if missing
aws s3 mb s3://snapstyle-images-yourname
```

---

### Issue: Tables Not Being Created

**Symptoms:**
- `relation "users" does not exist`
- Database has no tables

**Solutions:**
```bash
# Option 1: Let the app create them (automatic)
# Just run the server, it creates tables on startup

# Option 2: Create manually
python3
>>> from app.database import engine, Base
>>> from app.models import User, SearchHistory, Favorite, UserInteraction
>>> Base.metadata.create_all(bind=engine)
>>> exit()

# Option 3: Use Alembic migrations
pip install alembic
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head

# Verify tables exist
psql snapstyle
\dt  # Should list: users, search_history, favorites, user_interactions
```

---

## iOS Issues

### Issue: "No Development Team"

**Symptoms:**
- "Signing for 'SnapStyleAI' requires a development team"
- Can't build the app

**Solutions:**
1. **Add Apple ID to Xcode:**
   - Xcode → Preferences → Accounts
   - Click "+" button
   - Add Apple ID
   - Sign in

2. **Select Team:**
   - Click project in Xcode
   - Select "SnapStyleAI" target
   - Signing & Capabilities tab
   - Team dropdown → Select your Apple ID

3. **Free Account Limitations:**
   - Free accounts work for testing!
   - Apps expire after 7 days (just rebuild)
   - Can't share via TestFlight (need $99/year membership)

---

### Issue: "Failed to Register Bundle Identifier"

**Symptoms:**
- Bundle ID already taken
- Can't provision profile

**Solutions:**
1. **Change Bundle Identifier:**
   - Signing & Capabilities tab
   - Change to unique ID: `com.yourname.snapstyleai.unique123`

2. **Add Random Suffix:**
   ```
   com.yourname.snapstyle.abc123
   com.yourname.snapstyleai.test
   ```

3. **Check Apple Developer Portal:**
   - https://developer.apple.com
   - Identifiers section
   - See if bundle ID exists

---

### Issue: App Won't Build

**Symptoms:**
- Build fails with various errors
- "Command failed" errors

**Solutions:**
```
1. Clean Build Folder:
   Product → Clean Build Folder (Cmd + Shift + K)

2. Delete Derived Data:
   Xcode → Preferences → Locations
   Click arrow next to Derived Data path
   Delete the SnapStyleAI folder

3. Restart Xcode
   Close completely (Cmd + Q)
   Reopen project

4. Update Xcode:
   Check App Store for updates

5. Check for Syntax Errors:
   Look at errors in Issue Navigator (Cmd + 5)
   Fix any red errors one by one
```

---

### Issue: Cannot Connect to Backend

**Symptoms:**
- Login fails
- "Connection refused" errors
- API calls timeout

**Solutions:**

**For Simulator:**
```swift
// In APIService.swift:
private let baseURL = "http://localhost:8000"
// This should work!
```

**For Physical Device:**
```swift
// Must use your Mac's IP address:
private let baseURL = "http://192.168.1.XXX:8000"

// Find your IP:
// Terminal: ifconfig | grep "inet " | grep -v 127.0.0.1
// Or: System Preferences → Network → WiFi → Advanced → TCP/IP
```

**Check Backend:**
```bash
# 1. Make sure backend is running
# Terminal should show: "Uvicorn running on http://127.0.0.1:8000"

# 2. Test from terminal
curl http://localhost:8000/health
# Should return: {"status":"healthy"}

# 3. Check firewall isn't blocking
# System Preferences → Security & Privacy → Firewall
# Allow incoming connections for Python

# 4. For physical device on same WiFi
ping 192.168.1.XXX  # Should respond
curl http://192.168.1.XXX:8000/health  # Should work
```

---

### Issue: Camera Not Working

**Symptoms:**
- Camera button doesn't work
- Black screen when taking photo
- "Camera not available"

**Solutions:**

1. **Simulator Limitation:**
   - Camera ONLY works on physical devices
   - Use "Choose from Library" in simulator
   - Or test on real iPhone

2. **Permission Denied:**
   - Settings → Privacy → Camera
   - Enable for SnapStyleAI
   - Or: Delete app and reinstall

3. **Info.plist Missing:**
   - Check `NSCameraUsageDescription` exists
   - Check `NSPhotoLibraryUsageDescription` exists

---

### Issue: Login/Signup Fails

**Symptoms:**
- "Invalid credentials" errors
- Nothing happens when tapping Sign Up
- Error messages in console

**Solutions:**

1. **Check Backend Logs:**
   ```bash
   # Look in backend terminal for errors
   # Should see: POST /api/auth/register - 200 OK
   ```

2. **Check Network Connection:**
   ```swift
   // Add debug prints in APIService.swift:
   func post<T: Encodable, R: Decodable>(_ path: String, body: T) async throws -> R {
       print("📤 POST to: \(baseURL)\(path)")
       // ... rest of code
   }
   ```

3. **Verify Email Format:**
   - Must be valid email: `test@example.com`
   - Not just `test` or `test@`

4. **Check Database:**
   ```bash
   psql snapstyle
   SELECT * FROM users;
   # See if user was created
   ```

---

### Issue: Images Not Uploading

**Symptoms:**
- Upload times out
- "Failed to upload image" error
- Search never completes

**Solutions:**

1. **Check S3 Configuration:**
   - Backend `.env` has correct AWS credentials
   - S3 bucket exists and is accessible
   - Bucket allows public uploads

2. **Check Image Size:**
   - Backend compresses images before S3
   - But very large images (>20MB) might timeout
   - Try smaller test images first

3. **Check Backend Logs:**
   ```bash
   # Look for S3 upload errors
   # Should see: "Uploading to S3: ..."
   ```

4. **Test S3 Directly:**
   ```bash
   # In backend directory:
   python3
   >>> from app.utils.image import s3_client
   >>> s3_client.list_buckets()
   # Should list your buckets
   ```

---

## Database Issues

### Issue: Cannot Create Database

**Symptoms:**
```bash
createdb: error: connection to server failed
# or
createdb: error: database "snapstyle" already exists
```

**Solutions:**
```bash
# 1. Start PostgreSQL
brew services start postgresql

# 2. Check if database exists
psql -l | grep snapstyle

# 3. If exists, drop and recreate
dropdb snapstyle
createdb snapstyle

# 4. If PostgreSQL not installed
brew install postgresql
brew services start postgresql

# 5. Check PostgreSQL is running
ps aux | grep postgres
# Should see postgres processes
```

---

### Issue: Permission Denied

**Symptoms:**
```
permission denied for database
permission denied to create database
```

**Solutions:**
```bash
# 1. Connect as postgres user
psql postgres

# 2. Grant permissions
CREATE ROLE your_username WITH LOGIN;
ALTER ROLE your_username CREATEDB;

# 3. Or use postgres user
psql -U postgres
CREATE DATABASE snapstyle;
GRANT ALL PRIVILEGES ON DATABASE snapstyle TO your_username;

# 4. Update DATABASE_URL in .env
DATABASE_URL=postgresql://your_username@localhost:5432/snapstyle
```

---

### Issue: Database Encoding Errors

**Symptoms:**
```
invalid byte sequence for encoding "UTF8"
UnicodeDecodeError
```

**Solutions:**
```bash
# Create database with UTF-8
dropdb snapstyle
createdb -E UTF8 snapstyle

# Or in psql:
CREATE DATABASE snapstyle ENCODING 'UTF8';
```

---

## API Issues

### Issue: CORS Errors

**Symptoms:**
- Browser console: "CORS policy blocked"
- API calls fail from web browser
- Works in Postman but not in browser

**Solutions:**
```python
# In backend/app/main.py, check CORS settings:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# For production, specify exact origins:
allow_origins=["https://yourdomain.com"]
```

---

### Issue: JWT Token Expires

**Symptoms:**
- User gets logged out unexpectedly
- "Invalid authentication credentials" errors

**Solutions:**
```python
# In backend/.env, increase expiration:
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# Or implement refresh token logic
# Currently tokens last 7 days by default
```

---

### Issue: Rate Limiting / Too Many Requests

**Symptoms:**
- "429 Too Many Requests"
- Google Gemini quota exceeded

**Solutions:**
```python
# Implement caching in backend
# Cache Gemini responses for identical images

# Reduce API calls:
# - Cache product search results
# - Implement request debouncing in iOS
# - Add loading states to prevent duplicate requests
```

---

## Deployment Issues

### Issue: Environment Variables Not Loading

**Symptoms:**
- App works locally but crashes in production
- "Environment variable not found" errors

**Solutions:**
```bash
# 1. Check .env file exists in production
ls -la .env

# 2. Set environment variables in hosting platform
# Railway: Settings → Environment Variables
# Render: Dashboard → Environment → Add
# Heroku: Settings → Config Vars

# 3. Verify variables are loaded
python3
>>> from app.config import settings
>>> print(settings.GOOGLE_GEMINI_API_KEY)
# Should print your key (first few chars)
```

---

### Issue: Database Connection in Production

**Symptoms:**
- "Connection refused" to database
- "Could not connect to database" in production

**Solutions:**
```bash
# 1. Use production DATABASE_URL
# Not localhost! Use managed database URL

# 2. Format: postgresql://user:pass@host:5432/dbname
# Example: postgresql://user:pass@db.railway.app:5432/railway

# 3. Enable SSL if required
# Add ?sslmode=require to URL

# 4. Check database is accessible
psql "your-production-database-url"
```

---

### Issue: iOS App Can't Connect to Production Backend

**Symptoms:**
- App works with localhost but not production URL
- "NSAppTransportSecurity" errors

**Solutions:**
```swift
// 1. Update baseURL in APIService.swift
private let baseURL = "https://your-backend.railway.app"

// 2. Must use HTTPS in production (not HTTP)
// Railway, Render provide HTTPS automatically

// 3. If using HTTP (not recommended):
// Add to Info.plist:
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

---

## Still Having Issues?

### Debug Checklist

**Backend:**
```bash
# 1. Check logs
tail -f logs/app.log

# 2. Enable debug mode
# In .env:
DEBUG=true

# 3. Test each component
python3 -c "from app.services.gemini import gemini_service; print('Gemini OK')"
python3 -c "from app.database import engine; print('Database OK')"
```

**iOS:**
```
1. Check Xcode console (Cmd + Shift + Y)
2. Look for error messages
3. Add print statements in code
4. Use breakpoints to debug
5. Check network requests in console
```

**Database:**
```bash
# 1. Connect to database
psql snapstyle

# 2. Check tables
\dt

# 3. Check data
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM search_history;

# 4. Check connections
SELECT * FROM pg_stat_activity;
```

---

## Get Help

If you're still stuck:

1. **Check the logs** - Most issues show up in logs
2. **Google the error** - Exact error message often has solutions
3. **Check GitHub Issues** - See if others had same problem
4. **Stack Overflow** - FastAPI and SwiftUI communities are helpful

---

## Common Success Checks

Everything working? You should see:

**Backend:**
- ✅ Server starts without errors
- ✅ Can access http://localhost:8000/docs
- ✅ Health check returns {"status": "healthy"}
- ✅ Can register a user via API docs

**iOS:**
- ✅ App builds and launches
- ✅ Can create account and login
- ✅ Can upload/take photos
- ✅ Search returns results
- ✅ Recommendations load

**Database:**
- ✅ Tables exist (`\dt` shows 4 tables)
- ✅ Can insert and query data
- ✅ Users table has test user

**APIs:**
- ✅ Gemini API key works
- ✅ S3 uploads successful
- ✅ Images accessible via URL

If all ✅, you're good to go! 🎉
