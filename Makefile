# Atajos del proyecto. En Windows sin `make`, usar los scripts de scripts/*.ps1.
.PHONY: up down build logs certs corpus loadtest test seed-ldap

up:            ## Levanta todo el stack
	docker compose up --build -d

down:          ## Baja el stack
	docker compose down

logs:          ## Logs en vivo
	docker compose logs -f api worker

certs:         ## Genera certificados self-signed para Nginx (TLS 1.3, RNF-002)
	bash scripts/gen_certs.sh

corpus:        ## Genera el corpus sintético (50 docs + 5 curados) en ./corpus
	python scripts/gen_corpus.py

loadtest:      ## Sube el corpus y cronometra la generación (RNF-004: 50 docs < 3 min)
	python scripts/loadtest.py

test:          ## Pruebas del backend
	docker compose run --rm worker pytest -q
