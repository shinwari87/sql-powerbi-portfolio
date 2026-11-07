CREATE TABLE products (
    sku TEXT PRIMARY KEY, product TEXT NOT NULL,
    price_cents INTEGER NOT NULL, unit_cost_cents INTEGER NOT NULL
);
CREATE TABLE order_lines (
    line_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, order_date TEXT NOT NULL,
    sku TEXT NOT NULL REFERENCES products, quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price_cents INTEGER NOT NULL, unit_cost_cents INTEGER NOT NULL
);
CREATE TABLE line_charges (
    charge_id TEXT PRIMARY KEY, line_id TEXT NOT NULL REFERENCES order_lines,
    kind TEXT NOT NULL CHECK(kind IN ('fee','shipping','refund')),
    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0)
);
CREATE TABLE advertising (
    month TEXT NOT NULL, sku TEXT NOT NULL REFERENCES products,
    spend_cents INTEGER NOT NULL CHECK(spend_cents >= 0), PRIMARY KEY(month, sku)
);
