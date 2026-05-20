# TikTok Scraper Pro - Extensión de Chrome

## Instalación

1. **Abrir Chrome** y navegar a `chrome://extensions/`

2. **Activar** "Modo de desarrollador" (esquina superior derecha)

3. **Hacer clic** en "Cargar descomprimida"

4. **Seleccionar** la carpeta `tiktok-extension`

5. La extensión aparecerá en tu barra de herramientas

## Uso

1. **Abrir** TikTok en Chrome: `https://www.tiktok.com/@alcaldiasa`

2. **Hacer clic** en el icono de la extensión (📱)

3. **Configurar** opciones:
   - ✅ Extraer comentarios de cada video
   - ✅ Cargar todos los videos del perfil

4. **Hacer clic** en "🚀 Iniciar Scraping"

5. **Esperar** a que complete (puede tomar varios minutos)

6. **Descargar** los datos cuando termine

## Datos que extrae

### Perfil
- Username
- Nombre
- Avatar
- Bio
- Seguidores
- Siguiendo
- Videos totales
- Verificado

### Videos (cada uno)
- ID del video
- Descripción
- Fecha de creación
- Vistas (views)
- Likes
- Comentarios
- Compartidas (shares)
- Favoritos (saves)
- Hashtags
- Menciones
- Música

### Comentarios (si está habilitado)
- Usuario
- Texto
- Likes
- Respuestas

## Formato de salida

JSON con esta estructura:
```json
{
  "profile": { ... },
  "videos": [
    {
      "video_id": "123456789",
      "description": "...",
      "create_time": "2025-01-15T10:30:00.000Z",
      "stats": {
        "views": 15000,
        "likes": 450,
        "comments": 32,
        "shares": 15,
        "saves": 20
      },
      "hashtags": ["#tiktok", "#trending"],
      "mentions": ["@user1"],
      "comments": [...]
    }
  ]
}
```

## Notas

- Los videos se cargan poco a poco al hacer scroll
- Para extraer TODOS los videos (2000+), aumenta el tiempo de espera
- Los comentarios requieren navegar a cada video individualmente
- Esta extensión funciona en el navegador, no es un bot automatizado