import sqlite3
import os
import time
import json
from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.components.sensor import *
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import Geometry, ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading, ValueTypes


class KeyValue(Sensor, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    MODEL: ClassVar[Model] = Model(ModelFamily("mcvella", "key-value"), "key-value")

    def __init__(self, name: str):
        super().__init__(name)
        self.db_path = "/tmp/viam/keyvalue/keyvalue.db"
        # In-memory storage for fast access
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

    def _init_database(self):
        """Initialize the SQLite database with the required table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS key_value_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'string',
                    ttl_seconds INTEGER,
                    created_at REAL NOT NULL,
                    expires_at REAL
                )
            ''')
            conn.commit()

    def _load_from_database(self):
        """Load all key-value pairs from database into memory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key, value, value_type, ttl_seconds, created_at, expires_at 
                    FROM key_value_store
                ''')
                rows = cursor.fetchall()
            
            self._memory_store.clear()
            current_time = time.time()
            
            for row in rows:
                key, value, value_type, ttl_seconds, created_at, expires_at = row
                # Skip expired keys when loading
                if expires_at is None or expires_at > current_time:
                    # Deserialize JSON values
                    if value_type == 'json':
                        try:
                            deserialized_value = json.loads(value)
                        except json.JSONDecodeError:
                            # Fallback to string if JSON parsing fails
                            deserialized_value = value
                    else:
                        deserialized_value = value
                    
                    self._memory_store[key] = {
                        "value": deserialized_value,
                        "value_type": value_type,
                        "ttl_seconds": ttl_seconds,
                        "created_at": created_at,
                        "expires_at": expires_at
                    }
        except Exception as e:
            self.logger.error(f"Failed to load from database: {e}")

    def _save_to_database(self, key: str, value: Any, ttl_seconds: Optional[str], 
                         created_at: float, expires_at: Optional[float]):
        """Save a key-value pair to the database."""
        try:
            # Determine value type and serialize if needed
            if isinstance(value, (dict, list, int, float, bool)) or value is None:
                value_type = 'json'
                serialized_value = json.dumps(value)
            else:
                value_type = 'string'
                serialized_value = str(value)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO key_value_store (key, value, value_type, ttl_seconds, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (key, serialized_value, value_type, ttl_seconds, created_at, expires_at))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save to database: {e}")

    def _delete_from_database(self, key: str):
        """Delete a key-value pair from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM key_value_store WHERE key = ?', (key,))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to delete from database: {e}")

    def _cleanup_expired_keys(self):
        """Remove expired keys from memory and database."""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self._memory_store.items():
            if data["expires_at"] is not None and data["expires_at"] <= current_time:
                expired_keys.append(key)
        
        # Remove expired keys from memory
        for key in expired_keys:
            del self._memory_store[key]
            self._delete_from_database(key)

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Sensor component.
        The default implementation sets the name from the `config` parameter and then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both required and optional)

        Returns:
            Self: The resource
        """
        return super().new(config, dependencies)

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any required dependencies or optional dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Tuple[Sequence[str], Sequence[str]]: A tuple where the
                first element is a list of required dependencies and the
                second element is a list of optional dependencies
        """
        return [], []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both required and optional)
        """
        # Initialize the database when the resource is configured
        self._ensure_db_directory()
        self._init_database()
        # Load existing data into memory
        self._load_from_database()
        return super().reconfigure(config, dependencies)

    async def get_readings(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, SensorReading]:
        """Return all key/value pairs as sensor readings."""
        # If memory store is empty, try to load from database
        if not self._memory_store:
            self._load_from_database()
        
        self._cleanup_expired_keys()
        
        data = {}
        for key, key_data in self._memory_store.items():
            data[key] = {
                "value": key_data["value"],
                "created_at": key_data["created_at"],
                "expires_at": key_data["expires_at"]
            }
        
        return {"data": data}

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        """Handle key-value operations: set, get, delete, delete_all."""
        command_name = command.get("command")
        
        if command_name == "set":
            return await self._handle_set(command)
        elif command_name == "get":
            return await self._handle_get(command)
        elif command_name == "delete":
            return await self._handle_delete(command)
        elif command_name == "delete_all":
            return await self._handle_delete_all(command)
        else:
            return {"error": f"Unknown command: {command_name}"}

    async def _handle_set(self, command: Mapping[str, ValueTypes]) -> Mapping[str, ValueTypes]:
        """Handle the set command."""
        key = command.get("key")
        value = command.get("value")
        ttl_seconds = command.get("ttl_seconds")
        
        if key is None or value is None:
            return {"error": "Both 'key' and 'value' are required for set command"}
        
        current_time = time.time()
        expires_at = None
        ttl_str = None
        
        if ttl_seconds is not None:
            try:
                # Convert to string first, then to float for safety
                ttl_str = str(ttl_seconds)
                ttl_float = float(ttl_str)
                expires_at = current_time + ttl_float
            except (ValueError, TypeError):
                return {"error": "ttl_seconds must be a valid number"}
        
        # Store in memory
        self._memory_store[str(key)] = {
            "value": value,
            "ttl_seconds": ttl_seconds,
            "created_at": current_time,
            "expires_at": expires_at
        }
        
        # Back to database
        self._save_to_database(str(key), value, ttl_str, current_time, expires_at)
        
        return {"success": True, "key": str(key), "value": value}

    async def _handle_get(self, command: Mapping[str, ValueTypes]) -> Mapping[str, ValueTypes]:
        """Handle the get command."""
        key = command.get("key")
        
        if not key:
            return {"error": "'key' is required for get command"}
        
        self._cleanup_expired_keys()
        
        key_str = str(key)
        if key_str in self._memory_store:
            data = self._memory_store[key_str]
            return {
                "success": True,
                "key": key_str,
                "value": data["value"],
                "created_at": data["created_at"],
                "expires_at": data["expires_at"]
            }
        else:
            # If not in memory, try loading from database
            if not self._memory_store:
                self._load_from_database()
                # Check again after loading
                if key_str in self._memory_store:
                    data = self._memory_store[key_str]
                    return {
                        "success": True,
                        "key": key_str,
                        "value": data["value"],
                        "created_at": data["created_at"],
                        "expires_at": data["expires_at"]
                    }
            
            return {"error": f"Key '{key}' not found"}

    async def _handle_delete(self, command: Mapping[str, ValueTypes]) -> Mapping[str, ValueTypes]:
        """Handle the delete command."""
        key = command.get("key")
        
        if not key:
            return {"error": "'key' is required for delete command"}
        
        key_str = str(key)
        
        # Remove from memory
        if key_str in self._memory_store:
            del self._memory_store[key_str]
        
        # Remove from database
        self._delete_from_database(key_str)
        
        return {"success": True, "key": key_str, "deleted": True}

    async def _handle_delete_all(self, command: Mapping[str, ValueTypes]) -> Mapping[str, ValueTypes]:
        """Handle the delete_all command."""
        self._memory_store.clear()
        # Clear all keys from the database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM key_value_store')
            conn.commit()
        return {"success": True, "deleted_count": len(self._memory_store)}

    async def get_geometries(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> List[Geometry]:
        """Return the geometries of the component."""
        return []

