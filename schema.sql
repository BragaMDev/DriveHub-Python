-- Recria tudo do zero (filhas primeiro, por causa das chaves estrangeiras)
DROP TABLE IF EXISTS rentals;

DROP TABLE IF EXISTS employees;

DROP TABLE IF EXISTS customers;

DROP TABLE IF EXISTS cars;

CREATE TABLE
    cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marca TEXT NOT NULL,
        modelo TEXT NOT NULL,
        ano INTEGER,
        categoria TEXT,
        valor_diario DECIMAL NOT NULL,
        placa_veiculo TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL
    );

CREATE TABLE
    customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        telefone TEXT UNIQUE,
        cpf TEXT NOT NULL UNIQUE,
        habilitacao INTEGER NOT NULL
    );
    
CREATE TABLE
    rentals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        employee_id INTEGER,
        data_retirada DATE NOT NULL,
        data_devolucao DATE NOT NULL,
        preco DECIMAL, 
        status TEXT NOT NULL,
        FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
    );
    
CREATE TABLE
    employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        cargo TEXT NOT NULL
    );


-- Índices das colunas mais filtradas nas telas
CREATE INDEX idx_rentals_car ON rentals (car_id);

CREATE INDEX idx_rentals_status ON rentals (status);

CREATE INDEX idx_cars_status ON cars (status);
