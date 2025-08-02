# Vehicle Parking Management System

> MAD 2 Project Submission  
> **Student Name**: Sujit Laware  
> **Roll Number**: 22f3002016  
> **Email**: 22f3002016@ds.study.iitm.ac.in

---

## Project Overview

The **Vehicle Parking App** is a robust, full-stack web application built to efficiently manage 4-wheeler parking systems. It supports both **Admin** and **User** roles with role-based access and features such as automatic spot booking, real-time updates, cost calculation, performance visualization, and background tasks.

---

## Tech Stack

### Backend
- **Flask** – API development & server-side logic
- **Flask-SQLAlchemy** – ORM for SQLite database
- **Flask-Login / JWT** – Authentication & session control
- **SQLite** – Lightweight relational DB
- **Redis** – Caching layer & job queue
- **Celery** – Background job processing
- **Celery Beat** – Scheduler for periodic tasks

### Frontend
- **Vue.js** – Reactive UI components
- **Vue CLI** – Tooling for Vue-based development
- **Bootstrap** – Responsive styling
- **Chart.js** – Visual representation of analytics
- **Jinja2** – HTML templating (via CDN if needed)

---

## Database Schema

> *(Add a diagram here if available. If not, a textual structure can be added later.)*

---

## Key Features

### Core Functionalities
- **Authentication System** – Secure login for both admins and users
- **Admin Dashboard** – Manage lots, spots, users, and view analytics
- **User Panel** – Book, track, and release parking spots
- **Real-time Status** – Live updates on spot availability
- **Billing System** – Automated price calculation based on duration

### Advanced Features
- **Background Jobs**
  - Daily email reminders
  - Monthly usage reports
  - CSV exports (on demand)
- **Performance Optimization**
  - Redis caching for frequently accessed data
  - Cache expiry management
  - Optimized API response times
- **Analytics & Reports**
  - Visual dashboards with Chart.js
  - Revenue & usage tracking
  - User activity analysis

---

## Demo / Presentation

[View Project Presentation Video](https://drive.google.com/drive/folders/1i_iVS38cGJuU0cOwBt1fK5ZjCGa85zSS?usp=sharing)

---

## Getting Started

> *(These are example instructions. You can tailor them based on your repo structure.)*

### Backend Setup

```bash
git clone <repo-url>
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
