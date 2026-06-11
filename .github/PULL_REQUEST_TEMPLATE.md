## KrishiMitra — Pull Request

### What does this PR do?
<!-- Brief description of changes -->

### Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / code quality
- [ ] Data update (MSP prices, scheme details)
- [ ] Frontend update

### Pre-merge checklist

**Smoke checks**
- [ ] `python manage.py check` passes
- [ ] `python scripts/quick_services_check.py` passes (or production verification for large changes)

**Frontend**
- [ ] No spaced HTML tags (`< div >` style)
- [ ] Chat message class uses `${sender}-message` format
- [ ] `apiUrl()` used for API calls in `frontend/js/app.js`

**Data integrity**
- [ ] MSP / scheme data changes reviewed if touched

### Verification output (paste if run)
```
python manage.py check
python scripts/quick_services_check.py
```
