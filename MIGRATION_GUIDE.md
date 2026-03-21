# Migration Guide: Old → New Restaurant AI

This document explains what changed and how to use the new professional structure.

---

## What Changed

### Old Structure (Before)
```
llama.cpp/
├── simple_server.py        # Single file, everything mixed
├── server.py               # Multiple conflicting versions
├── server_backup.py
├── server_native.py
├── restaurant_chat.html
├── orders.db              # Database in root directory
└── (100+ llama.cpp files mixed in)
```

### New Structure (After)
```
restaurant-ai/              # Separate, clean project
├── app/
│   ├── main.py            # Single source of truth
│   ├── config.py          # Environment-based config
│   ├── models.py          # Validation models
│   ├── database.py        # DB operations
│   ├── tobi_ai.py         # AI logic
│   └── menu_data.py       # Menu data
├── static/                # Web files
├── data/                  # Database (persistent)
├── logs/                  # Application logs
├── .env                   # Configuration
├── requirements.txt       # Dependencies
├── Dockerfile
└── docker-compose.yml
```

---

## What Was Fixed

### 1. **File Organization**
- ❌ **Before**: 4 different server files, confusing which to use
- ✅ **After**: ONE file (`app/main.py`), clearly organized modules

### 2. **Configuration**
- ❌ **Before**: Hardcoded values in Python files
- ✅ **After**: `.env` file with all settings
  ```bash
  # .env
  PORT=8000
  DATABASE_URL=sqlite:///./data/orders.db
  MAGIC_PASSWORD=i'm on yelp
  ```

### 3. **Database Location**
- ❌ **Before**: `orders.db` in project root
- ✅ **After**: `data/orders.db` (proper data directory)

### 4. **Dependencies**
- ❌ **Before**: Installed ad-hoc, no version control
- ✅ **After**: `requirements.txt` with pinned versions

### 5. **Error Handling**
- ❌ **Before**: Generic errors, no logging
- ✅ **After**: Proper logging to files + console
  ```
  logs/app.log - All application logs
  ```

### 6. **Health Monitoring**
- ❌ **Before**: No health check
- ✅ **After**: `/health` endpoint for Docker/K8s

### 7. **Input Validation**
- ❌ **Before**: Raw input, no validation
- ✅ **After**: Pydantic models validate everything

### 8. **Docker Support**
- ❌ **Before**: Basic Dockerfile
- ✅ **After**: Multi-stage build + docker-compose

---

## How to Run the New Version

### Quick Start (Python)
```bash
cd restaurant-ai

# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment config
cp .env.example .env

# 3. Run the server
python -m app.main

# 4. Access
http://localhost:8000
http://localhost:8000/api/docs  # Swagger UI
```

### Docker (Recommended)
```bash
cd restaurant-ai

# Build and run
docker-compose up --build

# Access
http://localhost:8000
```

---

## Feature Comparison

| Feature | Old | New |
|---------|-----|-----|
| **Menu-Aware AI** | ✅ | ✅ |
| **Order Management** | ✅ | ✅ |
| **Magic Password** | ✅ | ✅ |
| **Health Check** | ❌ | ✅ |
| **Logging** | ❌ | ✅ File + Console |
| **Environment Config** | ❌ | ✅ .env file |
| **Input Validation** | ❌ | ✅ Pydantic |
| **API Documentation** | ❌ | ✅ Auto-generated |
| **Docker Support** | Basic | ✅ Production-ready |
| **Database Location** | Root | ✅ data/ directory |
| **Error Handling** | Basic | ✅ Comprehensive |

---

## Migrating Your Data

### Copy Orders Database
```bash
# If you have orders in the old database
cp ../orders.db restaurant-ai/data/orders.db
```

### Check Data Migration
```bash
# The new app will automatically use the existing database
python -m app.main

# Query an old order
curl http://localhost:8000/order/1732
```

---

## API Changes

### The API is backward compatible

All endpoints work exactly the same:

```bash
# Chat (unchanged)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What burgers do you have?"}'

# Order (unchanged)
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{"items": [{"name": "Burger", "price": 16, "quantity": 1}]}'

# NEW: Health check
curl http://localhost:8000/health
```

---

## For Junior Developers

### Best Practices Implemented

1. **Separation of Concerns**
   - Each file has ONE job
   - `main.py` = API endpoints
   - `database.py` = DB operations
   - `tobi_ai.py` = AI logic

2. **Configuration Management**
   - Never hardcode values
   - Use environment variables
   - Different configs for dev/prod

3. **Error Handling**
   - Log everything
   - Specific error messages
   - Health checks for monitoring

4. **Input Validation**
   - Validate ALL user input
   - Use Pydantic models
   - Return clear error messages

5. **Documentation**
   - README for users
   - Inline comments for developers
   - Auto-generated API docs

6. **Version Control**
   - `.gitignore` for sensitive files
   - Don't commit `.env` or `*.db`
   - Separate code from data

---

## Troubleshooting

### Old Server Still Running?
```bash
# Kill old server
# Find process using port 8000
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

### Dependencies Not Found?
```bash
pip install -r requirements.txt
```

### Database Errors?
```bash
# Delete and recreate
rm data/orders.db
python -m app.main  # Auto-creates new database
```

### Want to Revert?
```bash
# Your backup is safe!
cd ../restaurant-ai-backup-20251010-154607
cat RESTORE_INSTRUCTIONS.md
```

---

## Next Steps

Now that you have a professional foundation:

1. **Try Docker**: `docker-compose up`
2. **Explore API Docs**: http://localhost:8000/api/docs
3. **Add Tests**: See `tests/` directory
4. **Add Real AI**: Uncomment llama-server in docker-compose.yml
5. **Deploy**: The app is production-ready!

---

## Key Takeaways

- **Single Source of Truth**: ONE main.py, not 4 servers
- **Configuration**: Use `.env`, not hardcoded values
- **Organization**: Code in `app/`, data in `data/`, logs in `logs/`
- **Monitoring**: `/health` endpoint for Docker/K8s
- **Validation**: Pydantic prevents bad data
- **Logging**: Debug production issues easily
- **Docker**: Consistent environment everywhere

---

**Questions?** Read the [README.md](README.md) or check inline code comments!
