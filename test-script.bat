@echo off
echo Starting Home Assistant test instance for Tylö integration...
echo Test instance will be available at http://localhost:8124
echo.
echo Press Ctrl+C to stop the test instance
echo.

docker-compose -f docker-compose.test.yml up --remove-orphans