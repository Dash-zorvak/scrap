#!/bin/bash
# ============================================================
# LIMPIAR CREDENCIALES EXPUESTAS DEL HISTORIAL DE GIT
# Ejecutar UNA SOLA VEZ en la PC de desarrollo
# ============================================================

echo "=== Paso 1: Rotar credenciales primero ==="
echo ""
echo "Antes de limpiar el repo, genera nuevas credenciales:"
echo "  - Telegram: @BotFather → /revoke → nuevo token"
echo "  - Supabase: Settings → API → Regenerate anon key"
echo "  - Facebook: no uses esa cuenta para scraping"
echo ""
echo "Presiona Enter cuando hayas rotado las credenciales..."
read

echo ""
echo "=== Paso 2: Instalar BFG Repo Cleaner ==="
echo ""
echo "  # En macOS:"
echo "  brew install bfg"
echo ""
echo "  # En Linux (descargar jar):"
echo "  wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar"
echo "  alias bfg='java -jar bfg-1.14.0.jar'"
echo ""
echo "Presiona Enter para continuar..."
read

echo ""
echo "=== Paso 3: Crear archivo con strings a eliminar ==="
cat > /tmp/credentials_to_remove.txt << 'EOF'
8745098441:AAGrmS2X-zvuX-sExcscsH4t5J-7Em2ZUS8
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhzZmxnamR2YWVtanFiY21heHZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg4MzIwOTUsImV4cCI6MjA5NDQwODA5NX0.lT7BTQ_gwPLX0nN8M8m3w3XB8dDx8UDXwsi10fZiwg4
dagorosales40@gmail.com
hsflgjdvaemjqbcmaxvl
EOF

echo "  ✅ Archivo creado: /tmp/credentials_to_remove.txt"

echo ""
echo "=== Paso 4: Limpiar historial ==="
echo ""
echo "  # Desde la raíz del repositorio:"
echo "  bfg --replace-text /tmp/credentials_to_remove.txt"
echo "  git reflog expire --expire=now --all"
echo "  git gc --prune=now --aggressive"
echo "  git push --force"
echo ""

echo "=== Paso 5: Verificar que .gitignore incluye .env ==="
if grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo "  ✅ .env ya está en .gitignore"
else
    echo "  ⚠️  Agrega .env a .gitignore:"
    echo "  echo '.env' >> .gitignore"
fi

echo ""
echo "=== Paso 6: Reemplazar .env.example ==="
echo "  Copia el nuevo .env.example (sin credenciales reales) al repo"
echo "  git add .env.example"
echo "  git commit -m 'fix: remove exposed credentials from env example'"
echo "  git push"
echo ""
echo "✅ Proceso completo"
