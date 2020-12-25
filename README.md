# fastapi-project-template

## Локальный старт

Требуется предварительная установка

* python
* virtualenv

```bash
rm -rf env || true
python3.9 -m venv env
source env/bin/activate
make sync-requirements
make run-server
```
