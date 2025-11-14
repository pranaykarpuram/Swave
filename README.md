# Swave - Music Discovery App

[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/19BwrNgF)

A swipe-based music discovery app built with React and Django.

## Features

- **User Authentication**: Register and login with JWT tokens
- **Demo Mode**: Try the app without registration
- **Music Discovery**: Swipe through music recommendations
- **User Profiles**: Track preferences and listening history

## Quick Start

### Backend (Django)
```bash
python manage.py migrate
python manage.py runserver
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
```

## Demo Mode

Click "Try Demo Mode" on the login screen to explore the app without creating an account.

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Zustand
- **Backend**: Django, Django REST Framework, SQLite
- **Authentication**: JWT tokens with Simple JWT
