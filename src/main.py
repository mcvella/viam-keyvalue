import asyncio
from viam.module.module import Module
try:
    from models.key_value import KeyValue
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.key_value import KeyValue


if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
