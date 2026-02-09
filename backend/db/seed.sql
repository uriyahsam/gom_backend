INSERT OR IGNORE INTO plans(id,name,billing,price_pesewas,max_active_listings) VALUES
(1,'Starter','monthly',2000,10),
(2,'Basic','monthly',5000,30),
(3,'Standard','monthly',12000,80),
(4,'Pro','monthly',25000,200),
(5,'Elite','monthly',50000,500);

INSERT OR IGNORE INTO categories(slug,name) VALUES
('ebooks','E-books'),
('past-questions','Past Questions'),
('templates','Templates'),
('services','Services'),
('electronics','Electronics');
