# Bajar, resetear y levantar
docker compose down
docker compose run -e RESET_DB=true whatsapp-demo
0/# O en una línea con variable de entorno
$env:RESET_DB="true"; docker compose up
```

El contenedor va a loguear:
```
⚠️  RESET_DB=true — borrando database.db existente...
🗑️  database.db eliminada
📄 Initializing database...
✅ Database initialized successfully