#!/bin/bash
set -euo pipefail

# Enable nullglob so patterns that don't match expand to nothing instead of literal strings
shopt -s nullglob
files=( *.log *.json *.xml )
shopt -u nullglob

# Check if there are any files to delete
if [ ${#files[@]} -eq 0 ]; then
    echo "No .log, .json, or .xml files found in the current directory."
    exit 0
fi

echo "The following files will be securely deleted (shredded):"
for file in "${files[@]}"; do
    echo "  - $file"
done
echo

# Prompt the user for confirmation
read -p "Are you sure you want to shred these files? Please type 'yes' to confirm: " confirm

if [ "$confirm" = "yes" ]; then
    echo "Shredding files..."
    shred -v -z -u "${files[@]}"
    echo "Files shredded successfully."
else
    echo "Aborted. No files were deleted."
    exit 1
fi
