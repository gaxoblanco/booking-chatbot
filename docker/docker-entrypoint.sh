#!/bin/bash

echo "🚀 Starting WhatsApp Bot Setup..."
echo ""

# ==================================================
# DOMAIN CONFIGURATION
# ==================================================
if [ -n "$DOMAIN_PRESET" ]; then
    echo "📦 Configurando dominio desde variable de entorno: $DOMAIN_PRESET"
    
    # Apply preset using Python
    python -c "from src.config.domain_config import load_preset; load_preset('$DOMAIN_PRESET')"
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Preset '$DOMAIN_PRESET' no encontrado"
        echo "   Presets disponibles: SALUD, PSICOLOGIA, BELLEZA, LEGAL, FITNESS, EDUCACION, HOGAR"
        exit 1
    fi
    
    echo "✅ Domain configured: $DOMAIN_PRESET"
    
elif grep -q "^load_preset(" src/config/domain_config.py; then
    # Already configured in file
    CONFIGURED_DOMAIN=$(grep "^load_preset(" src/config/domain_config.py | sed "s/load_preset('\(.*\)')/\1/")
    echo "✅ Domain already configured: $CONFIGURED_DOMAIN"
else
    echo "⚠️  Warning: Domain not configured, usando configuración por defecto"
fi

echo ""

# ==================================================
# DATABASE INITIALIZATION
# ==================================================

# Si RESET_DB=true, borrar la DB existente para recrearla desde cero
# Uso: docker compose run -e RESET_DB=true whatsapp-demo
#   o: RESET_DB=true docker compose up
if [ "$RESET_DB" = "true" ]; then
    if [ -f "database.db" ]; then
        echo "⚠️  RESET_DB=true — borrando database.db existente..."
        rm database.db
        echo "🗑️  database.db eliminada"
    else
        echo "ℹ️  RESET_DB=true — no había database.db, continuando..."
    fi
fi

if [ ! -f "database.db" ]; then
    echo "📄 Initializing database..."
    python scripts/init_db.py
    
    if [ $? -ne 0 ]; then
        echo "❌ Database initialization failed"
        exit 1
    fi
    
    echo "✅ Database initialized successfully"
else
    echo "✅ Database already exists"
fi

echo ""
echo "📊 Database tables:"
python -c "
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name')
tables = [row[0] for row in cursor.fetchall()]
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'  ✅ {table}: {count} registros')
conn.close()
"
echo ""

# ==================================================
# AUTO-LOAD PROFESSIONALS FROM CSV (DEVELOPMENT)
# ==================================================
if [ "$FLASK_ENV" = "development" ] || [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "dev" ]; then
    echo "🔧 Modo desarrollo detectado"
    
    # Check current professional count
    PROF_COUNT=$(python -c "
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM professionals')
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null || echo "0")
    
    echo "📊 Profesionales actuales: $PROF_COUNT"
    
    # Try to find CSV file in multiple locations
    CSV_FILES=(
        "/app/data/profesionales_demo.csv"
        "/app/data/profesionales.csv"
        "/app/profesionales_demo.csv"
        "/app/profesionales.csv"
    )
    
    CSV_FOUND=""
    for CSV_FILE in "${CSV_FILES[@]}"; do
        if [ -f "$CSV_FILE" ]; then
            CSV_FOUND="$CSV_FILE"
            break
        fi
    done
    
    if [ -n "$CSV_FOUND" ]; then
        echo "📂 CSV encontrado: $CSV_FOUND"
        
        if [ "$PROF_COUNT" -eq "0" ]; then
            echo "📥 Cargando profesionales desde CSV..."
            python scripts/load_professionals_from_csv.py "$CSV_FOUND"
            
            if [ $? -eq 0 ]; then
                echo "✅ Profesionales cargados exitosamente"
                
                # Show count after loading
                NEW_COUNT=$(python -c "
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM professionals')
count = cursor.fetchone()[0]
conn.close()
print(count)
")
                echo "📊 Total profesionales: $NEW_COUNT"
            else
                echo "❌ Error al cargar profesionales"
            fi
        else
            echo "⏭️  Ya hay $PROF_COUNT profesionales registrados"
            echo "💡 Para recargar, elimina database.db y reinicia"
        fi
    else
        echo "⚠️  No se encontró CSV de profesionales"
        echo "💡 Monta el archivo en:"
        echo "   - /app/data/profesionales_demo.csv"
        echo "   - O copia con: docker cp profesionales.csv whatsapp-demo:/app/data/"
    fi
    
    echo ""
fi

# ==================================================
# GOOGLE CALENDAR CONFIGURATION CHECK
# ==================================================
echo "🗓️  Google Calendar:"
if [ -f "config/google/service-account.json" ]; then
    echo "  ✅ Service Account configurado"
    
    # Quick validation of professionals with calendar_id
    CALENDAR_COUNT=$(python -c "
import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute(\"SELECT COUNT(*) FROM professionals WHERE calendar_id IS NOT NULL AND calendar_id != ''\")
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null || echo "0")
    
    echo "  📊 Profesionales con Google Calendar: $CALENDAR_COUNT"
    
    if [ "$CALENDAR_COUNT" -eq "0" ] && [ "$PROF_COUNT" -gt "0" ]; then
        echo "  ⚠️  Ningún profesional tiene calendar_id configurado"
        echo "  💡 Verifica que el CSV tenga columna 'calendar_id'"
    fi
else
    echo "  ⚠️  Service Account no configurado"
    echo "  💡 Coloca service-account.json en config/google/"
fi

echo ""

# ==================================================
# ACCESS KEYS CONFIGURATION (DEPRECATED - OPCIONAL)
# ==================================================
# Este sistema de claves puede ser opcional o removido
if [ -n "$MASTER_ACCESS_KEY" ]; then
    echo "🔑 Master access key: configurada"
fi

# ==================================================
# STARTUP
# ==================================================
echo ""
echo "✅ Setup complete!"
echo "🚀 Starting application..."
echo ""
echo "┌────────────────────────────────────────┐"
echo "  📱 WhatsApp Bot Webhook"
echo "  🌐 Port: 5000"
echo "  📦 Dominio: ${DOMAIN_PRESET:-DEFAULT}"
if [ "$FLASK_ENV" = "development" ] || [ "$ENVIRONMENT" = "development" ]; then
    echo "  🔧 Modo: Development"
    echo "  📊 Profesionales: $PROF_COUNT"
    echo "  🗓️  Con Calendar: $CALENDAR_COUNT"
fi
echo "└────────────────────────────────────────┘"
echo ""

# Start the application
exec python -m src.api.whatsapp_handler