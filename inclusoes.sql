INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Toyota',
        'Corolla',
        2023,
        'Sedan',
        150.00,
        'ABC1D23',
        'disponível'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Honda',
        'Civic',
        2022,
        'Sedan',
        160.00,
        'XYZ9W87',
        'alugado'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Jeep',
        'Renegade',
        2024,
        'SUV',
        220.00,
        'JKL4M56',
        'disponível'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Fiat',
        'Argo',
        2023,
        'Hatch',
        90.00,
        'QWE3R45',
        'disponível'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Volkswagen',
        'T-Cross',
        2023,
        'SUV',
        200.00,
        'MNO7P89',
        'manutenção'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Hyundai',
        'HB20',
        2022,
        'Hatch',
        95.00,
        'RST2U34',
        'disponível'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Chevrolet',
        'Tracker',
        2024,
        'SUV',
        210.00,
        'VWX5Y67',
        'disponível'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Renault',
        'Kwid',
        2021,
        'Hatch',
        80.00,
        'DEF6G78',
        'alugado'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Nissan',
        'Kicks',
        2023,
        'SUV',
        190.00,
        'GHI0J12',
        'disponível'
    );

INSERT INTO
    cars (
        marca,
        modelo,
        ano,
        categoria,
        valor_diario,
        placa_veiculo,
        status
    )
VALUES
    (
        'Toyota',
        'Hilux',
        2024,
        'Picape',
        350.00,
        'STU4V56',
        'disponível'
    );

INSERT INTO
    customers (nome, email, telefone, cpf, habilitacao)
VALUES
    (
        'Ana Souza',
        'ana.souza@email.com',
        '(11) 98765-4321',
        '123.456.789-01',
        1
    );

INSERT INTO
    customers (nome, email, telefone, cpf, habilitacao)
VALUES
    (
        'Carlos Lima',
        'carlos.lima@email.com',
        '(11) 91234-5678',
        '987.654.321-09',
        1
    );

INSERT INTO
    customers (nome, email, telefone, cpf, habilitacao)
VALUES
    (
        'Mariana Costa',
        'mariana.costa@email.com',
        '(11) 99888-7766',
        '456.789.123-45',
        1
    );

INSERT INTO
    customers (nome, email, telefone, cpf, habilitacao)
VALUES
    (
        'Lucas Martins',
        'lucas.martins@email.com',
        '(11) 97777-8899',
        '321.654.987-12',
        1
    );


INSERT INTO employees (nome, email, senha, cargo) VALUES 
('João Lima', 'joao.lima@drivehub.com', 'senha123', 'Gerente');

INSERT INTO employees (nome, email, senha, cargo) VALUES 
('Beatriz Costa', 'beatriz.costa@drivehub.com', 'senha456', 'Atendente');

INSERT INTO employees (nome, email, senha, cargo) VALUES 
('Lucas Souza', 'lucas.souza@drivehub.com', 'senha789', 'Atendente');

INSERT INTO rentals (car_id, customer_id, data_retirada, data_devolucao, preco, status) VALUES 
(2, 1, '2026-06-01', '2026-06-05', 640.00, 'concluida');

INSERT INTO rentals (car_id, customer_id, data_retirada, data_devolucao, preco, status) VALUES 
(8, 2, '2026-06-10', '2026-06-15', 400.00, 'ativa');

INSERT INTO rentals (car_id, customer_id, data_retirada, data_devolucao, preco, status) VALUES 
(3, 3, '2026-06-20', '2026-06-25', 1100.00, 'pendente');