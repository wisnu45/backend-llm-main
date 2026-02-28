-- Seed default roles used by the application
INSERT INTO roles (name, description, is_protected) VALUES
    ('admin', 'Administrator with full system access', true),
    ('user', 'Regular user with standard access', true)
ON CONFLICT (name) DO NOTHING;
