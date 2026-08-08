import importlib
import pkgutil

# Импортируем все модули в этом пакете, чтобы сработали
# декораторы @response_listener внутри них
package_name = __name__

for _, module_name, _ in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{package_name}.{module_name}")
