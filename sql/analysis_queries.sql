
-- ==========================================
-- INSTAMART ANALYTICS
-- SEVEN SQL ANALYSIS QUERIES
-- ==========================================

-- 1. Total orders by status
SELECT
    status,
    COUNT(*) AS total_orders
FROM orders
GROUP BY status
ORDER BY total_orders DESC;


-- 2. Total revenue by product category
SELECT
    p.category,
    ROUND(SUM(o.order_amount), 2) AS total_revenue
FROM orders o
JOIN products p
    ON o.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 3. Top 10 customers by spending
SELECT
    c.customer_id,
    c.city,
    ROUND(SUM(o.order_amount), 2) AS total_spending
FROM customers c
JOIN orders o
    ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.city
ORDER BY total_spending DESC
LIMIT 10;


-- 4. Average delivery time by city
SELECT
    c.city,
    ROUND(AVG(o.delivery_minutes), 2) AS avg_delivery_minutes
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
    AND o.delivery_minutes IS NOT NULL
GROUP BY c.city
ORDER BY avg_delivery_minutes;


-- 5. Monthly revenue analysis
SELECT
    strftime('%Y-%m', order_ts) AS order_month,
    ROUND(SUM(order_amount), 2) AS monthly_revenue
FROM orders
WHERE status = 'completed'
GROUP BY order_month
ORDER BY order_month;


-- 6. Ticket count by category
SELECT
    true_category,
    COUNT(*) AS total_tickets
FROM tickets
GROUP BY true_category
ORDER BY total_tickets DESC;


-- 7. Products ranked by quantity sold
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(o.quantity) AS total_quantity_sold
FROM orders o
JOIN products p
    ON o.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_quantity_sold DESC
LIMIT 10;