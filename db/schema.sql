PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id INTEGER NOT NULL UNIQUE,
  first_name TEXT,
  username TEXT,
  role TEXT NOT NULL DEFAULT 'customer',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vendors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  store_name TEXT NOT NULL,
  sell_type TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  location TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vendor_payout_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER NOT NULL UNIQUE,
  method TEXT NOT NULL,
  momo_network TEXT,
  momo_number TEXT,
  bank_name TEXT,
  bank_account_number TEXT,
  account_name TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  billing TEXT NOT NULL,
  price_pesewas INTEGER NOT NULL,
  max_active_listings INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER NOT NULL UNIQUE,
  plan_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  renews_at TEXT,
  paystack_reference TEXT,
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS categories (
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  short_description TEXT NOT NULL,
  long_description TEXT NOT NULL,
  category_slug TEXT,
  price_pesewas INTEGER NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  stock_status TEXT NOT NULL DEFAULT 'in_stock',
  cover_image_file_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
  FOREIGN KEY (category_slug) REFERENCES categories(slug) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS product_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL,
  telegram_file_id TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_digital_assets (
  product_id INTEGER PRIMARY KEY,
  telegram_file_id TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wishlists (
  user_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, product_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS carts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cart_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  qty INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  total_pesewas INTEGER NOT NULL DEFAULT 0,
  paystack_reference TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  paid_at TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  vendor_id INTEGER NOT NULL,
  product_type TEXT NOT NULL,
  name_snapshot TEXT NOT NULL,
  price_pesewas INTEGER NOT NULL,
  qty INTEGER NOT NULL DEFAULT 1,
  commission_pesewas INTEGER NOT NULL DEFAULT 0,
  vendor_net_pesewas INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS order_delivery_details (
  order_id INTEGER PRIMARY KEY,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  region TEXT NOT NULL,
  city TEXT NOT NULL,
  address TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vendor_order_status (
  order_id INTEGER NOT NULL,
  vendor_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (order_id, vendor_id),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  purpose TEXT NOT NULL,
  order_id INTEGER,
  vendor_id INTEGER,
  reference TEXT NOT NULL UNIQUE,
  amount_pesewas INTEGER NOT NULL,
  status TEXT NOT NULL,
  raw_event_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS wallet_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  reason TEXT NOT NULL,
  amount_pesewas INTEGER NOT NULL,
  order_id INTEGER,
  withdrawal_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS withdrawal_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER NOT NULL,
  amount_pesewas INTEGER NOT NULL,
  status TEXT NOT NULL,
  requested_at TEXT NOT NULL DEFAULT (datetime('now')),
  decision_at TEXT,
  decided_by_user_id INTEGER,
  paid_reference TEXT,
  paid_at TEXT,
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
  FOREIGN KEY (decided_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS vendor_uploads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  telegram_file_id TEXT NOT NULL,
  file_name TEXT,
  mime_type TEXT,
  file_size INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  used_in_product_id INTEGER,
  FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE,
  FOREIGN KEY (used_in_product_id) REFERENCES products(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS admins (
  telegram_id INTEGER PRIMARY KEY
);

-- lightweight state for bot uploads
CREATE TABLE IF NOT EXISTS upload_states (
  telegram_id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
