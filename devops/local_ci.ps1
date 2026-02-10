param(
    [string]$Message = "Auto-commit after successful local CI"
)

# Stop execution on error
$ErrorActionPreference = "Stop"

function Start-Step($Name, $Command) {
    Write-Host "`n--- $Name ---" -ForegroundColor Yellow
    # Execute command and capture exit code
    & powershell -Command $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAILED: $Name (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
        Write-Host "Auto-Push aborted. Please fix the errors above." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "Starting Local CI & Auto-Push..." -ForegroundColor Cyan

# 1. Linting
Start-Step "Ruff Linting" "uv run ruff check solo_mcp frontend tests"

# 2. Type Checking
Start-Step "Mypy Type Checking" "uv run mypy solo_mcp --ignore-missing-imports"

# 3. Testing
Start-Step "Pytest" "uv run pytest tests"

# Success branch
Write-Host "`n[PASS] All checks passed! Proceeding to Git Push..." -ForegroundColor Cyan

# 4. Git Operations
Write-Host "`n[4/4] Git Commit & Push..." -ForegroundColor Yellow
git add .
# Identify if there are any changes to commit
$status = git status --porcelain
if ($null -eq $status -or $status -eq "") {
    Write-Host "No changes to commit. Proceeding to push..." -ForegroundColor Gray
}
else {
    git commit -m $Message
}

git push

Write-Host "`nSuccess! All operations completed. CI/CD will now take over GitHub-side." -ForegroundColor Green
