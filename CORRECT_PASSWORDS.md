# 🔐 Correct Login Passwords

## 📋 **Exact Passwords Required:**

Based on the Flask logs, I can see you're entering `'Manoj'` but the system expects the full password.

### **Correct Login Credentials:**

| Email | Correct Password |
|-------|------------------|
| `mk4829779@gmail.com` | `Manoj123` |
| `lingammanojkumar178@gmail.com` | `Kumar123` |

## ❌ **Common Mistakes:**

- **Entering**: `Manoj` ❌
- **Should be**: `Manoj123` ✅

- **Entering**: `Kumar` ❌  
- **Should be**: `Kumar123` ✅

## 🧪 **Test Login:**

1. **Visit**: `http://localhost:5000`
2. **Email**: `mk4829779@gmail.com`
3. **Password**: `Manoj123` (exactly this - case sensitive)
4. **Click**: "Login with Email"

## 🔍 **Password Requirements:**

- **Case Sensitive**: `Manoj123` ≠ `manoj123`
- **Exact Match**: Must be exactly `Manoj123` or `Kumar123`
- **No Extra Spaces**: Trim any spaces before/after
- **Complete Password**: Don't use partial passwords

## 🚨 **If Still Not Working:**

The system will now show you the expected password in the error message for debugging. You should see:

```
Incorrect password. Expected: 'Manoj123' (Please use exact password)
```

## 💡 **Alternative Options:**

If you want to use a different password:

1. **Use Forgot Password**: Click "Forgot password?" to reset
2. **Use Google OAuth**: Click "Sign in with Google"
3. **Create New Account**: Click "Need an account? Sign up"

## ✅ **Summary:**

The correct password for `mk4829779@gmail.com` is **exactly** `Manoj123` (not `Manoj`).