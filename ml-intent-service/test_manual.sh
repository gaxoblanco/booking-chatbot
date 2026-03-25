#!/bin/bash
# test_manual.sh
# Script para testing manual del ML Intent Service
# Uso: ./test_manual.sh

set -e

echo "================================================"
echo "  ML INTENT SERVICE - TESTING MANUAL"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

echo -e "${BLUE}🔍 Verificando que el servicio esté corriendo...${NC}"
if curl -f -s "${BASE_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ Servicio está corriendo${NC}"
else
    echo -e "${YELLOW}⚠️  Servicio no está corriendo. Inicialo con:${NC}"
    echo "   docker-compose up -d"
    exit 1
fi

echo ""
echo "================================================"
echo "TEST 1: Health Check"
echo "================================================"
curl -X GET "${BASE_URL}/health" | jq '.'

echo ""
echo "================================================"
echo "TEST 2: Predicción - search_professional"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": "necesito psicólogo mañana"}' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 3: Predicción - greeting"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": "hola"}' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 4: Predicción - view_my_appointments"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": "ver mis turnos"}' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 5: Predicción - cancel_appointment"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": "cancelar turno"}' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 6: Predicción con typos"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": "nesesito psicologo maÃ±ana"}' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 7: Batch Prediction"
echo "================================================"
curl -X POST "${BASE_URL}/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      "necesito psicólogo",
      "ver mis turnos",
      "hola",
      "cancelar cita"
    ]
  }' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 8: Mensaje desconocido"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": "asdfgh qwerty"}' \
  | jq '.'

echo ""
echo "================================================"
echo "TEST 9: Error - mensaje vacío"
echo "================================================"
curl -X POST "${BASE_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"message": ""}' \
  | jq '.'

echo ""
echo "================================================"
echo "✅ TESTS COMPLETADOS"
echo "================================================"
echo ""
echo "📊 Para ver la documentación interactiva:"
echo "   ${BASE_URL}/docs"
echo ""
