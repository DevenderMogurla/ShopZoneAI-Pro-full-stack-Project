
# ShopZoneAI Pro — Flask e-commerce project

A polished full-stack e-commerce demo based on your uploaded Flask + MySQL project concepts. It includes customer registration/login, product catalogue and details, search/categories, cart, stock validation, checkout, a Razorpay-style **dummy/test payment**, order tracking, admin product management, customer management, order fulfilment, low-stock alerts, sales dashboard and a built-in shopping help assistant.

## Important payment note
The included checkout is a **local payment simulation only**. It does not call Razorpay, accept real card/UPI details, or charge money. This is safe for project demonstrations. To accept real payments, integrate Razorpay's official test/live APIs on the server and verify signatures before marking orders paid.

## 1. Requirements
- Windows 10/11
- Python 3.10 or newer
- VS Code (recommended)

## 2. Extract and open
1. Extract `ShopZoneAI_Pro.zip`.
2. Open the `ShopZoneAI_Pro` folder in VS Code.
3. Open Terminal → New Terminal.

## 3. Create virtual environment (PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If PowerShell blocks activation, use Command Prompt:
```bat
.venv\Scripts\activate.bat
```
Or run without activation:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 4. Configure
Copy `.env.example` to `.env`. The default SQLite database is created automatically, so **no MySQL setup is required to run the demo**. Keep the default database setting for your first run.

Optional MySQL:
1. Create a database in MySQL Workbench:
```sql
CREATE DATABASE shopzone_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
2. Install driver:
```powershell
pip install pymysql
```
3. In `.env`, set:
```env
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/shopzone_ai
```
4. Restart the app. Tables and demo products are created automatically.

## 5. Start project
```powershell
python app.py
```
Open **http://127.0.0.1:5000** in Chrome. Keep terminal running while using the site. Press `Ctrl+C` to stop.

## 6. Admin login
Default demo admin:
- URL: `http://127.0.0.1:5000/login`
- Email: `admin@shopzone.local`
- Password: `Admin@123`

Change these in `.env` before exposing the app to any network. Never deploy with the default credentials or development secret key.

### Add a product (admin)
1. Sign in with the admin credentials above.
2. Click **Admin** in the top navigation.
3. Open **Products** in the left control-center menu.
4. Click **Add product**.
5. Enter product name, category, description, selling price, MRP, stock.
6. Optionally upload a JPG/PNG/WEBP/GIF image (max 5MB).
7. Tick **Featured product** if it should appear on the homepage.
8. Keep **Published / visible** checked.
9. Click **Save product**. The product is now visible in the customer storefront.

## 7. Customer journey: register, buy and track
1. Click **Create account** and register using your own email and a password of at least 8 characters.
2. Sign in with that customer account.
3. Open **Shop**, select a product and view its details.
4. Choose quantity and click **Add to cart**.
5. Open **Cart**, update quantities or remove items, then **Proceed to checkout**.
6. Enter the delivery address and click **Continue to test payment**.
7. Click **Simulate successful payment**. This creates a test payment reference and marks the order paid; no money is charged.
8. Open **My Orders → Track** to see the order, items, payment status and fulfilment status.
9. Admin can update fulfilment status to Processing, Shipped, Out for delivery or Delivered. The customer sees the update in My Orders.

## 8. Admin features
- Dashboard: product/customer/order counts, paid-test revenue, pending fulfilment and low-stock alerts.
- Products: add, edit, publish/hide, upload product images and search.
- Orders: inspect customer, address, items, total, payment reference and update delivery status.
- Customers: view customer accounts and enable/disable user access.

## 9. AI assistant
Open **AI Assistant** in the navbar. It provides in-app guided help for products, cart, test checkout, order tracking and admin product management. This starter assistant uses a local intent/FAQ flow and does not require an external AI API key. It is easy to replace with an LLM API later.

## 10. Project structure
```text
ShopZoneAI_Pro/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── shopzone.db              # generated on first run
├── database/                # reserved for future data layer modules
├── static/
│   ├── style.css
│   ├── phone.svg ...        # demo product artwork
│   └── uploads/             # uploaded product images
└── templates/
    ├── base.html
    ├── home.html
    ├── products.html
    ├── product.html
    ├── auth.html
    ├── cart.html
    ├── checkout.html
    ├── payment.html
    ├── orders.html
    ├── order_detail.html
    ├── assistant.html
    └── admin/
```

## Troubleshooting
- `ModuleNotFoundError`: activate `.venv`, then `pip install -r requirements.txt`.
- MySQL connection error: use SQLite first (leave `DATABASE_URL` unset), or verify MySQL is running, database exists, password is correct and `pymysql` is installed.
- Port 5000 busy: change `app.run(debug=True, port=5001)` and open `http://127.0.0.1:5001`.
- Admin login fails: check `.env` admin email/password. The first admin is seeded when the database is created. If you change credentials after a DB was already seeded, update the admin user in the database or remove `shopzone.db` to reset demo data (this deletes demo orders/users).
- Product images: upload through Admin → Products → Add Product. Demo products use local SVG artwork.

## Security checklist before deployment
Set a strong `SECRET_KEY`, change the seeded admin password, enable HTTPS, add CSRF protection and rate limiting, configure secure session cookies, validate uploaded image content, and integrate real payment verification. This demo is for local academic demonstration, not production financial processing.
