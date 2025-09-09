#!/bin/bash

# sync-docs.sh - Sync *.spec.md files to docs structure
# This script finds all *.spec.md files, copies them to docs/src/content/docs/spec/
# and adds appropriate frontmatter headers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_SPEC_DIR="$PROJECT_ROOT/docs/src/content/docs/spec"

echo -e "${YELLOW}🔄 Syncing *.spec.md files to documentation...${NC}"

# Create spec directory if it doesn't exist
mkdir -p "$DOCS_SPEC_DIR"

# Find all *.spec.md files
spec_files=($(find "$PROJECT_ROOT" -name "*.spec.md" -type f))

if [ ${#spec_files[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No *.spec.md files found${NC}"
    exit 0
fi

echo -e "${GREEN}📁 Found ${#spec_files[@]} spec file(s):${NC}"

# Process each spec file
for spec_file in "${spec_files[@]}"; do
    # Get relative path from project root
    rel_path="${spec_file#$PROJECT_ROOT/}"
    
    # Extract filename without extension
    filename=$(basename "$spec_file" .spec.md)
    
    # Create a clean title from filename (replace underscores with spaces, title case)
    title=$(echo "$filename" | sed 's/_/ /g' | sed 's/\b\w/\U&/g')
    
    # Create target file path
    target_file="$DOCS_SPEC_DIR/$filename.md"
    
    echo -e "  📄 Processing: $rel_path"
    echo -e "     → $target_file"
    
    # Create frontmatter header
    cat > "$target_file" << EOF
---
title: $title
description: Component specification and documentation
---

EOF
    
    # Append the original content (skip the first line if it's a title)
    if head -n1 "$spec_file" | grep -q "^# "; then
        # Skip the first line if it's a markdown title
        tail -n +2 "$spec_file" >> "$target_file"
    else
        # Include all content if no title
        cat "$spec_file" >> "$target_file"
    fi
    
    echo -e "     ✅ Created: $target_file"
done

echo -e "${GREEN}🎉 Successfully synced ${#spec_files[@]} spec file(s) to documentation!${NC}"
echo -e "${YELLOW}💡 Don't forget to update astro.config.mjs sidebar to include the spec section${NC}"
