#!/bin/bash

echo "=========================================="
echo "Reloading V3 + Context KG Extension"
echo "=========================================="

BASE_URL="http://localhost:7200"
REPOS=("BG_Retailer" "BG_Wholesaler" "BG_Distributor" "BG_Factory")

# Step 1: Clean
echo -e "\n1. Cleaning repositories..."
for repo in "${REPOS[@]}"; do
    echo "   Cleaning $repo..."
    curl -s -X DELETE $BASE_URL/repositories/$repo/statements > /dev/null
done

# Step 2: Load ontology
echo -e "\n2. Loading ontology..."
for repo in "${REPOS[@]}"; do
    echo "   Loading to $repo..."
    curl -s -X POST $BASE_URL/repositories/$repo/statements \
      -H "Content-Type: application/x-turtle" \
      --data-binary @beer_game_ontology.ttl > /dev/null
done

# Step 3: Load SHACL
echo -e "\n3. Loading SHACL..."
for repo in "${REPOS[@]}"; do
    echo "   Loading to $repo..."
    curl -s -X POST $BASE_URL/repositories/$repo/statements \
      -H "Content-Type: application/x-turtle" \
      --data-binary @beer_game_shacl.ttl > /dev/null
done

# Step 4: Load initial data
echo -e "\n4. Loading initial data (Week 1)..."
curl -s -X POST $BASE_URL/repositories/BG_Retailer/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_retailer_kg_v3.ttl > /dev/null
echo "   ✓ Retailer"

curl -s -X POST $BASE_URL/repositories/BG_Wholesaler/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_wholesaler_kg_v3.ttl > /dev/null
echo "   ✓ Wholesaler"

curl -s -X POST $BASE_URL/repositories/BG_Distributor/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_distributor_kg_v3.ttl > /dev/null
echo "   ✓ Distributor"

curl -s -X POST $BASE_URL/repositories/BG_Factory/statements \
  -H "Content-Type: application/x-turtle" \
  --data-binary @beer_game_factory_kg_v3.ttl > /dev/null
echo "   ✓ Factory"

echo -e "\n=========================================="
echo "✓ V3 + Context KG loaded successfully!"
echo "Ready to run: cd SWRL_Rules && python advanced_simulation_v3.py"
echo "=========================================="
