# ==========================================
# CREAR: init_and_run.sh
# ==========================================

#!/bin/bash

echo "🚀 Iniciando aplicación PSIVALE..."

# Esperar un momento para asegurar que la BD esté lista
sleep 2

# Verificar si ya existen profesionales de prueba
PROF_COUNT=$(python -c "
from database import db
stats = db.get_stats()
print(stats.get('total_professionals', 0))
" 2>/dev/null || echo "0")

echo "📊 Profesionales actuales en BD: $PROF_COUNT"

# Si no hay profesionales, crear los de prueba
if [ "$PROF_COUNT" -lt 3 ]; then
    echo "📝 Creando profesionales de prueba..."
    python create_test_professionals_simple.py
else
    echo "✅ Ya existen profesionales en la BD, omitiendo creación"
fi

# Iniciar el servidor
echo "🌐 Iniciando servidor Flask..."
python whatsapp_handler.py