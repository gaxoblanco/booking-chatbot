#!/bin/bash

echo "🚀 Starting WhatsApp Bot Setup..."
echo ""

# Check if domain is configured via environment variable
if [ -n "$DOMAIN_PRESET" ]; then
    echo "📦 Configurando dominio desde variable de entorno: $DOMAIN_PRESET"
    
    # Apply preset using Python
    python -c "from domain_config import load_preset; load_preset('$DOMAIN_PRESET')"
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Preset '$DOMAIN_PRESET' no encontrado"
        echo "   Presets disponibles: SALUD, PSICOLOGIA, BELLEZA, LEGAL, FITNESS, EDUCACION, HOGAR"
        exit 1
    fi
    
    echo "✅ Domain configured: $DOMAIN_PRESET"
    
elif grep -q "^load_preset(" domain_config.py; then
    # Already configured in file
    CONFIGURED_DOMAIN=$(grep "^load_preset(" domain_config.py | sed "s/load_preset('\(.*\)')/\1/")
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
    echo "   docker-compose exec whatsapp-bot python setup_domain.py"
    echo ""
    exit 1
fi

# Check if database exists
if [ ! -f "database.db" ]; then
    echo "🔄 Initializing database..."
    python init_db.py
    
    if [ $? -ne 0 ]; then
        echo "❌ Database initialization failed"
        exit 1
    fi
fi

echo ""
echo "✅ Setup complete!"
echo "🚀 Starting application..."
echo ""

# Start the application
exec python whatsapp_handler.py