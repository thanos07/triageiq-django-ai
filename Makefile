.PHONY: backend frontend test seed

backend:
	cd backend && python manage.py runserver

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest

seed:
	cd backend && python manage.py seed_demo
