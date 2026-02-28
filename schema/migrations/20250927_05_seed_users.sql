-- Seed default admin and user accounts (password: Secret123)
INSERT INTO users (roles_id, name, username, password, is_portal, is_protected) VALUES
    ((SELECT id FROM roles WHERE name = 'admin'), 'John Doe', 'admin', 'scrypt:32768:8:1$nusZhRrOd5doyN5Q$707a6abd60e15f76a01d7ad4108c9250d473b503eddeefafd54bd981c9e77e253d01ac03f71783939cd561b23b95c549d92fb01947231dd7b0fe1dbbd893a26a', false, true),
    ((SELECT id FROM roles WHERE name = 'user'), 'Jane Smith', 'user', 'scrypt:32768:8:1$4gUkg31prmEiLtpR$0470f3ced66445a77a6a4d24dc7be4fdb1c08d71960fd4477ca3045252e788d41d44990d85cf26ee8dbc1d1107393be5c9764bf1ecc04289259eb88a1dff6575', false, false)
ON CONFLICT (username) DO NOTHING;
