# Module key-value 

A Viam sensor component that provides high-performance key-value storage with TTL (Time To Live) support. Data is kept in memory for fast access and backed to SQLite database located at `/tmp/viam/keyvalue/keyvalue.db` for persistence.

## Model mcvella:key-value:key-value

A sensor component that provides key-value storage operations through do_command calls. The `get_readings()` method returns all stored key-value pairs. All operations are performed in memory for maximum performance while maintaining persistence through SQLite backing.

### Configuration
The following attribute template can be used to configure this model:

```json
{}
```

This model doesn't require any configuration attributes.

#### Example Configuration

```json
{}
```

### DoCommand

This model implements DoCommand with the following supported operations:

#### Set Command
Set or update a key-value pair with optional TTL. **Values can be any JSON-serializable type, including numbers, booleans, lists, dicts, and even falsy values like `0`, `false`, or `""`.**

```json
{
  "command": "set",
  "key": "my_key",
  "value": "my_value",
  "ttl_seconds": 3600
}
```

##### Examples of valid values:
```json
{"command": "set", "key": "int_key", "value": 0}
{"command": "set", "key": "bool_key", "value": false}
{"command": "set", "key": "empty_str", "value": ""}
{"command": "set", "key": "list_key", "value": [1, 2, 3]}
{"command": "set", "key": "dict_key", "value": {"a": 1, "b": 2}}
```

Parameters:
- `command`: Must be "set"
- `key`: The key to store (required, must not be null)
- `value`: The value to store (required, must not be null; can be any JSON-serializable type, including 0, false, or "")
- `ttl_seconds`: Time to live in seconds (optional, if not provided the key won't expire)

Response:
```json
{
  "success": true,
  "key": "my_key",
  "value": "my_value"
}
```

#### Get Command
Retrieve a value by key.

```json
{
  "command": "get",
  "key": "my_key"
}
```

Parameters:
- `command`: Must be "get"
- `key`: The key to retrieve (required)

Response:
```json
{
  "success": true,
  "key": "my_key",
  "value": "my_value",
  "created_at": 1703123456.789,
  "expires_at": 1703127056.789
}
```

#### Delete Command
Delete a key-value pair.

```json
{
  "command": "delete",
  "key": "my_key"
}
```

Parameters:
- `command`: Must be "delete"
- `key`: The key to delete (required)

Response:
```json
{
  "success": true,
  "key": "my_key",
  "deleted": true
}
```

#### Delete All Command
Delete all key-value pairs from the store.

```json
{
  "command": "delete_all"
}
```

Parameters:
- `command`: Must be "delete_all"

Response:
```json
{
  "success": true,
  "deleted_count": 0
}
```

### GetReadings

The `get_readings()` method returns all stored key-value pairs as sensor readings:

```json
{
  "key1": {
    "value": "value1",
    "created_at": 1703123456.789,
    "expires_at": null
  },
  "key2": {
    "value": 0, 
    "created_at": 1703123456.789,
    "expires_at": 1703127056.789
  },
  "key3": {
    "value": false,
    "created_at": 1703123456.789,
    "expires_at": null
  },
  "key4": {
    "value": [1,2,3],
    "created_at": 1703123456.789,
    "expires_at": null
  },
  "key5": {
    "value": {"a": 1, "b": 2},
    "created_at": 1703123456.789,
    "expires_at": null
  }
}
```

### Features

- **High Performance**: All key-value pairs are stored in memory for ultra-fast access
- **Persistent Storage**: Data is automatically backed to SQLite database at `/tmp/viam/keyvalue/keyvalue.db`
- **TTL Support**: Keys can have an expiration time set in seconds
- **Automatic Cleanup**: Expired keys are automatically removed from both memory and database
- **Thread Safe**: Uses SQLite for thread-safe concurrent access with in-memory caching
- **Simple API**: Easy-to-use do_command interface for all operations
- **Automatic Directory Creation**: The database directory is created automatically if it doesn't exist
- **Data Persistence**: All data survives service restarts through SQLite backing
- **Full JSON Support**: Values can be any JSON-serializable type, including numbers, booleans, lists, dicts, and falsy values like 0, false, or ""
