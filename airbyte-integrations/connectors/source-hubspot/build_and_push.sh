#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"


set -e  # Exit immediately if any command fails

# File to store the last used tag
LAST_TAG_FILE=".last_source_hubspot_tag"

# Read the last tag, if it exists
if [ -f "$LAST_TAG_FILE" ]; then
    LAST_TAG=$(cat "$LAST_TAG_FILE")
else
    LAST_TAG="0.0.2"
    echo "No previous tag found. Using default: $LAST_TAG"
fi

# Prompt for new tag, with default suggestion
read -e -p "Enter new tag [${LAST_TAG}]: " NEW_TAG
NEW_TAG="${NEW_TAG:-$LAST_TAG}"  # Fallback to old tag if input is empty

# Save the new tag
echo "$NEW_TAG" > "$LAST_TAG_FILE"

# Show where airbyte-ci is
echo "Using airbyte-ci from: $(which airbyte-ci)"
echo ""

# Step 1: Build
echo "=== STEP 1: Building connector ==="
airbyte-ci connectors --name source-hubspot build --tag=0.0.1 --architecture=linux/amd64

# Step 2: Tag Docker image
echo ""
echo "=== STEP 2: Tagging Docker image ==="
docker tag airbyte/source-hubspot:0.0.1 belkhojayev/source-hubspot-custom:$NEW_TAG

# Step 3: Push Docker image
echo ""
echo "=== STEP 3: Pushing Docker image ==="
docker push belkhojayev/source-hubspot-custom:$NEW_TAG

echo ""
echo "✅ Done. Image pushed with tag: $NEW_TAG"
