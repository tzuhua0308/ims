-- ============================================================
-- 庫存管理系統 — Supabase 資料表初始化
-- 在 Supabase > SQL Editor 執行此檔案
-- ============================================================

-- 品項主表
CREATE TABLE IF NOT EXISTS ims_products (
  id         SERIAL PRIMARY KEY,
  code       TEXT UNIQUE,
  name       TEXT NOT NULL,
  ref_price  NUMERIC DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 進貨紀錄
CREATE TABLE IF NOT EXISTS ims_purchases (
  id           SERIAL PRIMARY KEY,
  year         INT  NOT NULL,
  period       INT  NOT NULL,
  date         DATE,
  invoice_type TEXT,
  invoice_no   TEXT,
  code         TEXT,
  product_name TEXT,
  unit_price   NUMERIC,
  qty          NUMERIC,
  vendor_name  TEXT,
  vendor_tax   TEXT,
  amount       NUMERIC,
  source_sheet TEXT,
  imported_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 銷貨紀錄
CREATE TABLE IF NOT EXISTS ims_sales (
  id             SERIAL PRIMARY KEY,
  year           INT  NOT NULL,
  period         INT  NOT NULL,
  machine_no     TEXT,
  date           DATE,
  invoice_no     TEXT,
  code           TEXT,
  product_name   TEXT,
  qty            NUMERIC,
  untaxed_amount NUMERIC,
  imported_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 費用紀錄
CREATE TABLE IF NOT EXISTS ims_expenses (
  id           SERIAL PRIMARY KEY,
  year         INT  NOT NULL,
  period       INT  NOT NULL,
  date         DATE,
  invoice_type TEXT,
  invoice_no   TEXT,
  content      TEXT,
  vendor_name  TEXT,
  vendor_tax   TEXT,
  amount       NUMERIC,
  imported_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 報廢紀錄
CREATE TABLE IF NOT EXISTS ims_scraps (
  id           SERIAL PRIMARY KEY,
  year         INT  NOT NULL,
  period       INT  NOT NULL,
  date         DATE,
  code         TEXT,
  product_name TEXT,
  qty          NUMERIC,
  reason       TEXT,
  loss         NUMERIC,
  note         TEXT,
  imported_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 效能索引
CREATE INDEX IF NOT EXISTS idx_purchases_year_period ON ims_purchases(year, period);
CREATE INDEX IF NOT EXISTS idx_sales_year_period     ON ims_sales(year, period);
CREATE INDEX IF NOT EXISTS idx_expenses_year_period  ON ims_expenses(year, period);
CREATE INDEX IF NOT EXISTS idx_scraps_year_period    ON ims_scraps(year, period);
CREATE INDEX IF NOT EXISTS idx_purchases_code        ON ims_purchases(code);
CREATE INDEX IF NOT EXISTS idx_sales_code            ON ims_sales(code);

-- Row Level Security（開啟 + 允許所有操作）
ALTER TABLE ims_products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE ims_purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE ims_sales     ENABLE ROW LEVEL SECURITY;
ALTER TABLE ims_expenses  ENABLE ROW LEVEL SECURITY;
ALTER TABLE ims_scraps    ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY['ims_products','ims_purchases','ims_sales','ims_expenses','ims_scraps']
  LOOP
    EXECUTE format(
      'CREATE POLICY IF NOT EXISTS "allow_all" ON %I FOR ALL USING (true) WITH CHECK (true)', tbl
    );
  END LOOP;
END $$;
