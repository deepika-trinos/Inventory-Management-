-- Runs automatically ONCE, the first time the Docker database is created
-- (see docker-compose.yml). Creates the separate database used only by pytest.
-- To run it again, reset the data:  docker compose down -v  then  docker compose up -d
CREATE DATABASE itam_test OWNER itam_app;
