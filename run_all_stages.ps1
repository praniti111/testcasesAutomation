# Windows PowerShell Script
# File: run_all_stages.ps1

param(
  [string]$repoPath
)

if (-not $repoPath) {
  Write-Error " Please provide the repo path as an argument."
  Write-Output "Usage: ./run_all_stages.ps1 -repoPath ./your-repo"
  exit 1
}

# Step 1: Run Jest with coverage
Write-Output " Running Jest to collect coverage..."
Push-Location $repoPath
npx jest --coverage --coverageReporters=json-summary
Pop-Location

# Step 2: Run TS function extractor
Write-Output " Scanning repo and extracting functions..."
ts-node src/scanner/repoScanner.ts $repoPath

# Step 3: Run embedding
Write-Output " Embedding functions into ChromaDB..."
python embedding/embed_repo.py

# Step 4: Generate prompts
Write-Output " Generating LLM prompts..."
python embedding/prompt_generator.py

# Step 5: Generate test cases
Write-Output " Generating Jest test files with Azure GPT..."
python embedding/generate_tests.py

Write-Output " All stages completed. Check test-output/ for generated tests."

Write-Output "`n Final Coverage Report:"
Push-Location $repoPath
npx jest --coverage --coverageReporters=text-summary
Pop-Location
