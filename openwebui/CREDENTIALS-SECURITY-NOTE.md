# 🚨 SECURITY NOTE: Credentials Excluded

**Date:** October 25, 2025
**Reporter:** Antoine Dubuc (adubuc@cloudgeometry.com)
**Status:** ✅ RESOLVED - All credentials excluded from repository

---

## Summary

The Open Web UI files received from Eugene originally contained hardcoded credentials. **All credential files have been excluded from this repository** and are documented locally for deployment configuration.

---

## Credential Files Excluded

The following files contained sensitive credentials and have been **excluded via .gitignore**:

1. **`openwebui/secrets/google-service-account.json`**
   - Contains: GCP Service Account credentials
   - Severity: CRITICAL

2. **`openwebui/backend/.env_1`**
   - Contains: API keys and OAuth secrets
   - Severity: CRITICAL

3. **`openwebui/env`**
   - Contains: Multiple OAuth credentials and API keys
   - Severity: CRITICAL

---

## Types of Credentials Found

| Credential Type | Count | Severity |
|----------------|-------|----------|
| Google Cloud Service Account (Private Key) | 1 | 🔴 CRITICAL |
| OpenAI API Keys | 1 | 🔴 CRITICAL |
| Google OAuth Client ID & Secret | 2 | 🟡 HIGH |
| Zoho OAuth Client ID & Secret | 1 | 🟡 HIGH |

**Total:** 5 credential sets across 3 files

---

## Configuration Required for Deployment

To deploy this application, you will need to configure the following **environment variables**:

### Google Cloud Platform
- `GCP_PROJECT_ID`
- `GCP_PRIVATE_KEY_ID`
- `GCP_PRIVATE_KEY`
- `GCP_SERVICE_ACCOUNT_EMAIL`
- `GCP_CLIENT_ID`

### OpenAI
- `OPENAI_API_KEY`

### Google OAuth (Drive Integration)
- `GOOGLE_DRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET`

### Zoho OAuth
- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`

---

## Security Actions Taken

✅ **All credential files excluded from git history**
✅ **Files added to .gitignore**
✅ **Local backups preserved in non-committed folder**
✅ **Clean branch created without any credential exposure**

---

## Deployment Instructions

1. **Create a `.env` file** (not committed to git) with the required environment variables
2. **Or use your deployment platform's secret management:**
   - AWS: Secrets Manager / Parameter Store
   - Docker: Environment variables in docker-compose
   - Kubernetes: Secrets and ConfigMaps
   - Heroku: Config vars

3. **Refer to `.env.example`** files for configuration templates

---

## Security Recommendations

### Immediate Actions
- ⚠️ **Rotate all credentials** that were in the original files
- ⚠️ **Review GCP audit logs** for the actionbridge project
- ⚠️ **Monitor OpenAI usage** for unauthorized activity

### Long-term
- Use secret management tools (AWS Secrets Manager, HashiCorp Vault, etc.)
- Implement automated secret scanning in CI/CD
- Regular credential rotation policy
- Least-privilege access principles

---

## Questions?

Contact Nick or Antoine for:
- Access to credential values for deployment
- Questions about the excluded files
- Security concerns or observations

---

**Note:** Actual credential values are **NOT included in this file** for security reasons. They are documented locally for authorized personnel only.
