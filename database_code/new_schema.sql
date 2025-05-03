-- 1. First, create the database and tables properly
CREATE DATABASE IF NOT EXISTS stationary_management;
USE stationary_management;

-- Users Table with auto-increment
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'employee', 'supplier', 'student') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_role (role)
);

-- Inventory Table
CREATE TABLE IF NOT EXISTS inventory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    stock INT NOT NULL DEFAULT 0,
    low_stock_threshold INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock (stock),
    CHECK (stock >= 0),
    CHECK (low_stock_threshold >= 0)
);

-- Departments Table
CREATE TABLE IF NOT EXISTS departments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

-- Employee Requests Table with proper constraints
CREATE TABLE IF NOT EXISTS employee_requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL,
    reason TEXT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    admin_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES inventory(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    CHECK (quantity > 0)
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(50) NOT NULL,
    record_id INT NOT NULL,
    action VARCHAR(10) NOT NULL,  -- INSERT/UPDATE/DELETE
    old_values JSON,
    new_values JSON,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 2. Fix the triggers (only need one version, remove duplicates)
DELIMITER //

CREATE TRIGGER inventory_after_update
AFTER UPDATE ON inventory
FOR EACH ROW
BEGIN
    -- Only log if stock actually changed
    IF NEW.stock != OLD.stock THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values)
        VALUES (
            'inventory', 
            NEW.id, 
            'UPDATE',
            JSON_OBJECT('stock', OLD.stock, 'low_stock_threshold', OLD.low_stock_threshold),
            JSON_OBJECT('stock', NEW.stock, 'low_stock_threshold', NEW.low_stock_threshold)
        );
    END IF;
END//
select * from inventory;
CREATE TRIGGER request_after_update
AFTER UPDATE ON employee_requests
FOR EACH ROW
BEGIN
    -- Only log status changes
    IF NEW.status != OLD.status THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values)
        VALUES (
            'employee_requests', 
            NEW.id, 
            'UPDATE',
            JSON_OBJECT('status', OLD.status),
            JSON_OBJECT('status', NEW.status)
        );
    END IF;
END//

DELIMITER ;

-- 3. Insert sample data
INSERT INTO departments (name, description) VALUES 
('HR', 'Handles employee relations and policies'),
('IT', 'Manages company technology and support'),
('Finance', 'Responsible for financial planning and reporting'),
('Operations', 'Oversees business operations and logistics'),
('Marketing', 'Handles advertising and promotions');

INSERT INTO categories (name, description) VALUES 
('Stationery', 'Office supplies like pens, paper, and notebooks'),
('Furniture', 'Chairs, desks, and cabinets'),
('Electronics', 'Devices such as printers, computers, and projectors'),
('Cleaning Supplies', 'Sanitizers, tissues, and disinfectants'),
('Miscellaneous', 'Other office essentials');

-- 4. Verification queries
SELECT * FROM users;
SELECT * FROM inventory;
SELECT * FROM departments;
SELECT * FROM employee_requests;
SELECT * FROM audit_logs ORDER BY changed_at DESC ;
SHOW INDEX FROM inventory;
SELECT * FROM inventory WHERE name = 'Notebook';

set sql_safe_updates=1;
-- Update inventory to test trigger

ALTER TABLE employee_requests 
MODIFY status ENUM('pending', 'approved', 'rejected', 'cleared') NOT NULL DEFAULT 'pending';
SELECT id, status FROM employee_requests WHERE status NOT IN ('pending', 'approved', 'rejected');
SELECT id, status FROM employee_requests WHERE status NOT IN ('pending', 'approved', 'rejected');

UPDATE employee_requests 
SET status = 'pending' 
WHERE status NOT IN ('pending', 'approved', 'rejected');





DELETE FROM employee_requests WHERE status = 'Cleared';
-- or if you want to fix it:
UPDATE employee_requests SET status = 'approved' WHERE status = 'Cleared';

CREATE TABLE employee_requests (
    id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL,
    reason TEXT,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    admin_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES inventory(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    CHECK (quantity > 0)
);

-- join
SELECT 
    d.name AS department_name,
    c.name AS category_name
FROM 
    departments d
CROSS JOIN 
    categories c
WHERE 
    c.name IN ('Stationery', 'Electronics');
    
-- sets
-- Set and display total departments
SET @dept_count = (SELECT COUNT(*) FROM departments);
SELECT @dept_count AS total_departments;

-- Set and display total categories
SET @cat_count = (SELECT COUNT(*) FROM categories);
SELECT @cat_count AS total_categories;




select * from departments;

-- Check audit log
SELECT * FROM audit_logs ORDER BY changed_at DESC;
SHOW TRIGGERS;







-- cursor

DELIMITER $$

CREATE PROCEDURE list_all_categories()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE cat_name VARCHAR(100);
    
    DECLARE cur CURSOR FOR SELECT name FROM categories;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;

    category_loop: LOOP
        FETCH cur INTO cat_name;
        IF done THEN
            LEAVE category_loop;
        END IF;
        SELECT CONCAT('Category: ', cat_name);
    END LOOP;

    CLOSE cur;
END$$

DELIMITER ;

-- Call the procedure
CALL list_all_categories();
