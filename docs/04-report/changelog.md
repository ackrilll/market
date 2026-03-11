# Changelog

All notable changes to the 365 건강농산 주문서 변환 시스템 are documented here.

## [2026-03-11] - Login + User Mapping Implementation

### Added
- **Authentication Module** (`auth.py`)
  - Login page with ID/password form
  - SHA-256 password hashing
  - Session-based authentication
  - User logout functionality
  - st.secrets integration for credential management

- **User Configuration System** (map.py enhancements)
  - Per-user vendor configuration isolation
  - `load_user_config(user_id)` for loading user-specific settings
  - `_get_current_config()` for prioritized config access (session_state → global)
  - `_get_current_vendor_map()` for user-specific vendor lookup
  - Path Traversal protection via `os.path.basename()` sanitization

- **Application Integration** (convert.py modifications)
  - Authentication gate at application entry point
  - Dynamic header display showing logged-in user
  - Dynamic sidebar profile information
  - Logout button in sidebar
  - Post-login user config loading

- **User Data Files**
  - `data/users/admin/vendor_config.json` (28 vendors, full access)
  - `data/users/test/vendor_config.json` (empty vendor list, test isolation)
  - `.streamlit/secrets.toml` (admin/test account credentials)

### Changed
- **convert.py**
  - Inserted auth gate at `main()` entry point
  - Replaced static nh_list import with dynamic `get_nh_list()` calls
  - Added post-login `load_user_config()` call
  - Added user display name to header and sidebar

- **map.py**
  - All vendor lookup functions now use `_get_current_config()`
  - All CRUD operations save to user-specific path
  - Enhanced `_save_config()` with optional `config_path` parameter
  - Added helper functions for user config management

- **.gitignore**
  - Added `.streamlit/secrets.toml` to protect credentials

### Security
- Implemented SHA-256 password hashing (no plaintext storage)
- Added Path Traversal protection for file access
- Unified error messages to prevent information leakage
- Atomic file writes using tempfile and shutil.move
- Secured credentials in .gitignore

### Metrics
- **Design Match Rate**: 93% (PASS ✅)
- **Files Created**: 4
- **Files Modified**: 3
- **Lines of Code Added**: ~400
- **Security Checks Passed**: 6/6
- **Iterations Required**: 0 (first-pass completion)

### Documentation
- Completion Report: `docs/04-report/features/login-user-mapping.report.md`
- Analysis Report: `docs/03-analysis/login-user-mapping.analysis.md`

---

## Version History Summary

| Version | Date | Feature | Status |
|---------|------|---------|--------|
| 1.0 | 2026-03-11 | Login + User Mapping | ✅ Complete |

