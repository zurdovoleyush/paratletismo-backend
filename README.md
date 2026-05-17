# Sistema de Gestion de Torneos de Paratletismo

Aplicacion web completa para gestionar torneos de paratletismo.

## Tecnologias

- **Backend**: Django 5 + Django REST Framework
- **Frontend**: React 18 + Vite
- **Base de datos**: SQLite3 (desarrollo) / MySQL (produccion)
- **Autenticacion**: JWT

## Roles de Usuario

1. **Superadmin** - Acceso total al sistema
2. **Oficial** - Valida clasificaciones funcionales
3. **Administrador de Torneo** - Crea y gestiona torneos
4. **Institucion** - Gestiona perfil, atletas, entrenadores
5. **Entrenador** - Gestiona atletas e inscripciones
6. **Atleta** - Se inscribe y consulta resultados
7. **Juez Principal** - Designa jueces
8. **Juez** - Registra resultados

## Instalacion

### Backend
```bash
cd paratletismo-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

### Frontend
```bash
cd paratletismo-frontend
npm install
npm run dev
```

## Credenciales por Defecto
- **Email**: admin@paratletismo.com
- **Contraseña**: admin123
