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
    echo "❌ Error: Domain not configured"
    echo ""
    echo "Por favor configura el dominio de una de estas formas:"
    echo ""
    echo "1. Variable de entorno en .env:"
    echo "   DOMAIN_PRESET=PSICOLOGIA"
    echo ""
    echo "2. O ejecuta manualmente:"
    echo "   docker-compose exec whatsapp-bot python scripts/setup_domain.py"
    echo ""
    exit 1
fi

# ==================================================
# DATABASE INITIALIZATION
# ==================================================
if [ ! -f "data/database.db" ]; then
    echo "📄 Initializing database..."
    python scripts/init_db.py
    
    if [ $? -ne 0 ]; then
        echo "❌ Database initialization failed"
        exit 1
    fi
    
    echo ""
    echo "📊 Database tables created:"
    python -c "
import sqlite3
conn = sqlite3.connect('data/database.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name')
tables = [row[0] for row in cursor.fetchall()]
expected = ['professionals', 'weekly_schedule', 'specific_free_slots', 'client_searches', 'clients', 'appointments', 'appointment_history', 'notifications']
print(f'  ✅ Total: {len(tables)} tablas')
for table in expected:
    if table in tables:
        print(f'  ✅ {table}')
    else:
        print(f'  ❌ {table} - FALTA')
conn.close()
"
    echo ""
else
    echo "✅ Database already exists"
    echo ""
    echo "📊 Database tables:"
    python -c "
import sqlite3
conn = sqlite3.connect('data/database.db')
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
fi

# ==================================================
# SEED TEST DATA (DEVELOPMENT ONLY)
# ==================================================
# Check if we're in development mode
if [ "$FLASK_ENV" = "development" ] || [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "dev" ]; then
    echo "🌱 Development mode detected - checking test data..."
    
    # Check if we have test professionals
    PROF_COUNT=$(python -c "
import sqlite3
conn = sqlite3.connect('data/database.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM professionals')
count = cursor.fetchone()[0]
conn.close()
print(count)
")
    
    if [ "$PROF_COUNT" -lt 3 ]; then
        echo "📝 Seeding test professionals..."
        
        # Run seed script
        python scripts/seed_test_data.py
        
        if [ $? -eq 0 ]; then
            echo "✅ Test professionals created successfully"
        else
            echo "⚠️  Warning: Could not create test professionals"
            echo "   Run manually: docker-compose exec whatsapp-bot python scripts/seed_test_data.py"
        fi
    else
        echo "✅ Test data already exists ($PROF_COUNT professionals)"
    fi
    
    echo ""
fi

# ==================================================
# ACCESS KEYS CONFIGURATION
# ==================================================
echo "🔑 Sistema de Claves de Acceso:"
echo ""

# Check if master key is configured
if [ -n "$MASTER_ACCESS_KEY" ]; then
    echo "  ✅ Master key configurada: ${MASTER_ACCESS_KEY:0:4}****"
else
    echo "  ⚠️  Master key no configurada (opcional)"
    echo "     Configura MASTER_ACCESS_KEY en .env para testing"
fi

# Check if professional keys are configured
if [ -n "$PROFESSIONAL_ACCESS_KEYS" ]; then
    echo "  ✅ Claves de profesionales configuradas"
else
    echo "  ⚠️  Claves de profesionales no configuradas"
    echo "     Configura PROFESSIONAL_ACCESS_KEYS en config.py"
fi

echo ""
echo "💡 Para generar nuevas claves, usa:"
echo "   docker-compose exec whatsapp-bot python scripts/generate_access_keys.py"
echo ""

# ==================================================
# STARTUP
# ==================================================
echo ""
echo "✅ Setup complete!"
echo "🚀 Starting application..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📱 WhatsApp Bot Webhook"
echo "  🌐 Port: 5000"
echo "  🔑 Sistema: Claves de Acceso"
echo "  📦 Dominio: $DOMAIN_PRESET"
if [ "$FLASK_ENV" = "development" ] || [ "$ENVIRONMENT" = "development" ]; then
    echo "  🔧 Modo: Development"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the application
exec python -m src.api.whatsapp_handler