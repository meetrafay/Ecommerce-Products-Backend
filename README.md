# 🛒 Ecommerce Products Backend

A Django-based backend for managing ecommerce products, inventory, user authentication, and nightly inventory updates via Celery.

---

## ✨ Features

- 🔐 User authentication with profile picture support
- 📦 Product CRUD operations and semantic search
- 📊 Inventory management with stock history tracking
- 🌙 Nightly inventory update via Celery and django-celery-beat
- 🔌 RESTful API endpoints for products and authentication
- 🐳 Docker support for local development and deployment

---

## 📁 Project Structure

```

Ecommerce-Products-Backend/
├── authentication/         # User authentication and profile management
├── data/                   # Mock product CSV data for nightly updates
├── media/                  # Uploaded media files (profile pics)
├── product\_api/            # Django project settings and URLs
├── products/               # Product and inventory management
├── entrypoint.sh           # Docker entrypoint script
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── manage.py               # Django management script
└── db.sqlite3              # SQLite database (for development)

````

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/meetrafay/Ecommerce-Products-Backend.git
cd Ecommerce-Products-Backend
````

### 2. Install Dependencies

Create a virtual environment and install requirements:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and set your environment variables (database, email, etc).

### 4. Database Migration

```bash
python manage.py migrate
```

### 5. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver
```

---

## ⏱ Celery & Django-Celery-Beat

Start Celery worker and beat for scheduled tasks:

```bash
celery -A product_api worker --loglevel=info
celery -A product_api beat --loglevel=info
```

---

## 🐳 Docker Usage

Build and run the project using Docker:

```bash
docker-compose up --build
```

---

## 🌐 API Endpoints

| Method | Endpoint                         | Description                               |
| ------ | -------------------------------- | ----------------------------------------- |
| GET    | `/api/products/`                 | List products (supports filtering/search) |
| POST   | `/api/products/`                 | Create a new product                      |
| GET    | `/api/products/<id>/`            | Retrieve product details                  |
| PUT    | `/api/products/<id>/`            | Update product                            |
| DELETE | `/api/products/<id>/`            | Delete product                            |
| POST   | `/api/products/search/`          | Semantic product search                   |
| GET    | `/api/products/insights/`        | Product insights (statistics, trending)   |
| POST   | `/api/products/discount/`        | Add/update product discount               |
| POST   | `/api/products/shopify-webhook/` | Shopify inventory update webhook          |
| ANY    | `/api/auth/`                     | User authentication endpoints             |

---

## 🌙 Nightly Inventory Update

* Reads [`data/mock_products.csv`](data/mock_products.csv) and updates product inventory at midnight.
* Scheduled via [`products/management/commands/schedule_nightly_task.py`](products/management/commands/schedule_nightly_task.py).
* Uses Celery tasks:

  * [`import_product_data`](products/tasks.py)
  * [`validate_and_update_inventory`](products/tasks.py)
  * [`generate_and_email_report`](products/tasks.py)
  * [`nightly_inventory_update`](products/tasks.py)

---

## ✅ Running Tests

```bash
python manage.py test
```

---

## 🔍 File References

* **Product model**: [`products.models.Product`](products/models.py)
* **Stock history**: [`products.models.StockHistory`](products/models.py)
* **Celery tasks**: [`products.tasks`](products/tasks.py)
* **Authentication app**: [`authentication`](authentication/)
* **API tests**: [`products.tests`](products/tests.py)

---

## 📝 License

MIT License

---

**For more details, see:**

* [`products/tasks.py`](products/tasks.py)
* [`products/tests.py`](products/tests.py)
* [`authentication/models.py`](authentication/models.py)
* [`product_api/settings.py`](product_api/settings.py)

```
