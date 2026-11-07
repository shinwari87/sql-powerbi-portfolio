-- One physical order line may have multiple charges. Roll them up before joining sales.
CREATE VIEW order_economics AS
WITH charges AS (
    SELECT line_id, SUM(CASE WHEN kind = 'fee' THEN amount_cents ELSE 0 END) AS fees,
           SUM(CASE WHEN kind = 'shipping' THEN amount_cents ELSE 0 END) AS shipping,
           SUM(CASE WHEN kind = 'refund' THEN amount_cents ELSE 0 END) AS refunds
    FROM line_charges GROUP BY line_id
)
SELECT o.*, SUBSTR(order_date,1,7) AS month,
       quantity * unit_price_cents AS gross, quantity * unit_cost_cents AS cogs,
       COALESCE(fees,0) AS fees, COALESCE(shipping,0) AS shipping,
       COALESCE(refunds,0) AS refunds
FROM order_lines AS o LEFT JOIN charges USING (line_id);

CREATE VIEW product_month AS
WITH sales AS (
    SELECT month, sku, SUM(quantity) AS units, SUM(gross) AS gross, SUM(cogs) AS cogs,
           SUM(fees) AS fees, SUM(shipping) AS shipping, SUM(refunds) AS refunds
    FROM order_economics GROUP BY month, sku
), periods AS (
    -- Preserve ad spend for a month and product even if there were no sales.
    SELECT month, sku FROM sales UNION SELECT month, sku FROM advertising
), ledger AS (
    SELECT p.month, p.sku, pr.product, COALESCE(s.units,0) AS units,
           COALESCE(s.gross,0) AS gross, COALESCE(s.cogs,0) AS cogs,
           COALESCE(s.fees,0) AS fees, COALESCE(s.shipping,0) AS shipping,
           COALESCE(s.refunds,0) AS refunds, COALESCE(a.spend_cents,0) AS ads
    FROM periods p JOIN products pr USING (sku)
    LEFT JOIN sales s USING (month,sku) LEFT JOIN advertising a USING (month,sku)
)
SELECT *, gross - refunds AS net_sales,
       gross - refunds - cogs - fees - shipping - ads AS contribution
FROM ledger;

CREATE VIEW sku_ranking AS
SELECT *, ROUND(100.0 * contribution / NULLIF(net_sales,0),1) AS margin_pct,
       DENSE_RANK() OVER (ORDER BY contribution DESC) AS profit_rank
FROM (SELECT sku, product, SUM(units) AS units, SUM(gross) AS gross,
             SUM(net_sales) AS net_sales, SUM(refunds) AS refunds,
             SUM(contribution) AS contribution FROM product_month GROUP BY sku, product);
