import os
import pandas as pd
from sqlalchemy import create_engine, text
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule

DB_URL = os.getenv(
    "DB_URL",
    "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres"
)

QUERIES = {
    "top_categories": """
      SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
             ROUND(SUM(oi.price),2) AS revenue
      FROM order_items oi
      JOIN products p ON p.product_id = oi.product_id
      LEFT JOIN product_category_name_translation t
        ON t.product_category_name = p.product_category_name
      JOIN orders o ON o.order_id = oi.order_id
      GROUP BY category
      ORDER BY revenue DESC
      LIMIT 12;
    """,
    "aov_by_state": """
      WITH order_totals AS (
        SELECT oi.order_id, SUM(oi.price) AS order_sum
        FROM order_items oi GROUP BY oi.order_id
      )
      SELECT c.customer_state, ROUND(AVG(ot.order_sum),2) AS avg_order_value
      FROM orders o
      JOIN order_totals ot ON ot.order_id = o.order_id
      JOIN customers c ON c.customer_id = o.customer_id
      GROUP BY c.customer_state HAVING COUNT(*)>=50
      ORDER BY avg_order_value DESC LIMIT 15;
    """,
    "monthly_revenue": """
      SELECT DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
             ROUND(SUM(oi.price),2) AS revenue
      FROM orders o
      JOIN order_items oi ON oi.order_id = o.order_id
      GROUP BY 1 ORDER BY 1;
    """
}

OUT_DIR = "exports"
OUT_FILE = os.path.join(OUT_DIR, "report_assignment2.xlsx")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    eng = create_engine(DB_URL)

    # создаём Excel
    with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
        total_rows = 0
        for sheet, sql in QUERIES.items():
            df = pd.read_sql(text(sql), eng)
            total_rows += len(df)
            df.to_excel(writer, sheet_name=sheet, index=False)
            print(f"[OK] {sheet}: {len(df)} rows")

    # применяем форматирование через openpyxl
    wb = load_workbook(OUT_FILE)
    for ws in wb.worksheets:
        ws.freeze_panes = "B2"                     # фиксируем шапку
        ws.auto_filter.ref = ws.dimensions         # включаем фильтры

        # условное форматирование по числовым колонкам
        for col in ws.iter_cols(min_col=2, max_col=ws.max_column, min_row=2):
            rng = f"{col[0].column_letter}2:{col[0].column_letter}{ws.max_row}"
            rule = ColorScaleRule(
                start_type="min", start_color="FFAA0000",
                mid_type="percentile", mid_value=50, mid_color="FFFFFF00",
                end_type="max", end_color="FF00AA00"
            )
            ws.conditional_formatting.add(rng, rule)

    wb.save(OUT_FILE)
    print(f"✅ Created {OUT_FILE}, {len(QUERIES)} sheets, {total_rows} rows")


if __name__ == "__main__":
    main()
