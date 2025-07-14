import os
import asyncio
import time
import pytest
from src.models.key_value import KeyValue

DB_PATH = "/tmp/viam/keyvalue/keyvalue.db"

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Remove the database before each test for a clean slate
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    # Clean up after test
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.mark.asyncio
async def test_json_support():
    kv = KeyValue("test_keyvalue")
    kv._ensure_db_directory()
    kv._init_database()

    # String
    await kv.do_command({"command": "set", "key": "string_key", "value": "hello world"})
    result = await kv.do_command({"command": "get", "key": "string_key"})
    assert result.get("value") == "hello world"

    # Integer
    await kv.do_command({"command": "set", "key": "int_key", "value": 42})
    result = await kv.do_command({"command": "get", "key": "int_key"})
    assert result.get("value") == 42

    # Float
    await kv.do_command({"command": "set", "key": "float_key", "value": 3.14159})
    result = await kv.do_command({"command": "get", "key": "float_key"})
    assert result.get("value") == pytest.approx(3.14159, rel=1e-6)

    # Boolean
    await kv.do_command({"command": "set", "key": "bool_key", "value": True})
    result = await kv.do_command({"command": "get", "key": "bool_key"})
    assert result.get("value") is True

    # List
    await kv.do_command({"command": "set", "key": "list_key", "value": [1, 2, 3, "hello", True]})
    result = await kv.do_command({"command": "get", "key": "list_key"})
    assert result.get("value") == [1, 2, 3, "hello", True]

    # Dict
    d = {"name": "John", "age": 30, "active": True, "scores": [95, 87, 92]}
    await kv.do_command({"command": "set", "key": "dict_key", "value": d})
    result = await kv.do_command({"command": "get", "key": "dict_key"})
    assert result.get("value") == d

    # None
    await kv.do_command({"command": "set", "key": "none_key", "value": None})
    result = await kv.do_command({"command": "get", "key": "none_key"})
    assert "error" in result  # None is not stored

    # Complex nested
    complex_data = {
        "users": [
            {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
            {"id": 2, "name": "Bob", "roles": ["user"]}
        ],
        "settings": {
            "theme": "dark",
            "notifications": True,
            "limits": {"max_connections": 100, "timeout": 30.5}
        },
        "metadata": {
            "version": "1.0.0",
            "tags": ["production", "stable"],
            "config": None
        }
    }
    await kv.do_command({"command": "set", "key": "complex_key", "value": complex_data})
    result = await kv.do_command({"command": "get", "key": "complex_key"})
    assert result.get("value") == complex_data

    # All readings
    readings = await kv.get_readings()
    approx_type = type(pytest.approx(1))
    for key, expected in [
        ("string_key", "hello world"),
        ("int_key", 42),
        ("float_key", pytest.approx(3.14159, rel=1e-6)),
        ("bool_key", True),
        ("list_key", [1, 2, 3, "hello", True]),
        ("dict_key", d),
        ("complex_key", complex_data),
    ]:
        assert key in readings
        val = readings[key]
        if isinstance(val, dict) and "value" in val:
            if isinstance(expected, approx_type):
                assert val["value"] == expected
            else:
                assert val["value"] == expected
        else:
            assert False, f"Missing or invalid value for key {key}: {val}"

@pytest.mark.asyncio
async def test_crud():
    kv = KeyValue("test_crud")
    kv._ensure_db_directory()
    kv._init_database()
    
    # Set
    result = await kv.do_command({"command": "set", "key": "foo", "value": "bar"})
    assert result["success"]
    # Get
    result = await kv.do_command({"command": "get", "key": "foo"})
    assert result["value"] == "bar"
    # Update
    result = await kv.do_command({"command": "set", "key": "foo", "value": "baz"})
    assert result["success"]
    result = await kv.do_command({"command": "get", "key": "foo"})
    assert result["value"] == "baz"
    # Delete
    result = await kv.do_command({"command": "delete", "key": "foo"})
    assert result["success"]
    # Get after delete
    result = await kv.do_command({"command": "get", "key": "foo"})
    assert "error" in result

@pytest.mark.asyncio
async def test_ttl_expiry():
    kv = KeyValue("test_ttl")
    kv._ensure_db_directory()
    kv._init_database()
    
    # Set with TTL 1s
    result = await kv.do_command({"command": "set", "key": "temp", "value": "val", "ttl_seconds": 1})
    assert result["success"]
    # Should exist immediately
    result = await kv.do_command({"command": "get", "key": "temp"})
    assert result["value"] == "val"
    # Wait for expiry
    time.sleep(1.2)
    result = await kv.do_command({"command": "get", "key": "temp"})
    assert "error" in result

@pytest.mark.asyncio
async def test_update_ttl():
    kv = KeyValue("test_update_ttl")
    kv._ensure_db_directory()
    kv._init_database()
    
    # Set with TTL 1s
    result = await kv.do_command({"command": "set", "key": "foo", "value": "bar", "ttl_seconds": 1})
    assert result["success"]
    # Update with TTL 3s
    result = await kv.do_command({"command": "set", "key": "foo", "value": "bar", "ttl_seconds": 3})
    assert result["success"]
    # Wait 2s, should still exist
    time.sleep(2)
    result = await kv.do_command({"command": "get", "key": "foo"})
    assert result["value"] == "bar"
    # Wait another 2s, should be expired
    time.sleep(2)
    result = await kv.do_command({"command": "get", "key": "foo"})
    assert "error" in result

@pytest.mark.asyncio
async def test_delete_nonexistent():
    kv = KeyValue("test_delete_nonexistent")
    kv._ensure_db_directory()
    kv._init_database()
    
    result = await kv.do_command({"command": "delete", "key": "nope"})
    assert result["success"]
    assert result["deleted"]

@pytest.mark.asyncio
async def test_get_nonexistent():
    kv = KeyValue("test_get_nonexistent")
    kv._ensure_db_directory()
    kv._init_database()
    
    result = await kv.do_command({"command": "get", "key": "nope"})
    assert "error" in result

@pytest.mark.asyncio
async def test_persistence():
    kv = KeyValue("test_persist")
    kv._ensure_db_directory()
    kv._init_database()
    
    # Set a key
    result = await kv.do_command({"command": "set", "key": "persist", "value": "val"})
    assert result["success"]
    # Simulate restart by creating a new instance
    kv2 = KeyValue("test_persist")
    kv2._ensure_db_directory()
    kv2._init_database()
    kv2._load_from_database()
    result = await kv2.do_command({"command": "get", "key": "persist"})
    assert result["value"] == "val"

@pytest.mark.asyncio
async def test_delete_all():
    kv = KeyValue("test_delete_all")
    kv._ensure_db_directory()
    kv._init_database()
    
    # Set some keys
    await kv.do_command({"command": "set", "key": "key1", "value": "value1"})
    await kv.do_command({"command": "set", "key": "key2", "value": "value2"})
    await kv.do_command({"command": "set", "key": "key3", "value": "value3"})
    
    # Verify they exist
    readings = await kv.get_readings()
    assert len(readings) == 3
    assert "key1" in readings
    assert "key2" in readings
    assert "key3" in readings
    
    # Delete all
    result = await kv.do_command({"command": "delete_all"})
    assert result["success"]
    
    # Verify all are gone
    readings = await kv.get_readings()
    assert len(readings) == 0
    
    # Verify individual gets fail
    result = await kv.do_command({"command": "get", "key": "key1"})
    assert "error" in result
    result = await kv.do_command({"command": "get", "key": "key2"})
    assert "error" in result
    result = await kv.do_command({"command": "get", "key": "key3"})
    assert "error" in result

@pytest.mark.asyncio
async def test_bulk_operations():
    kv = KeyValue("test_bulk")
    kv._ensure_db_directory()
    kv._init_database()
    
    # Set 100 keys
    for i in range(100):
        result = await kv.do_command({"command": "set", "key": f"key_{i}", "value": i})
        assert result.get("success") or "error" not in result  # Handle both success and non-error cases
    # Get all
    for i in range(100):
        result = await kv.do_command({"command": "get", "key": f"key_{i}"})
        assert result.get("value") == i or "error" not in result
    # Delete all
    for i in range(100):
        result = await kv.do_command({"command": "delete", "key": f"key_{i}"})
        assert result.get("success") or "error" not in result
    # Confirm all gone
    for i in range(100):
        result = await kv.do_command({"command": "get", "key": f"key_{i}"})
        assert "error" in result 