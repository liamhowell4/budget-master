# Backend API Contract for MCP Chat Frontend

This document specifies the exact API endpoints, request formats, and response formats required for any backend to work with the MCP Chat frontend application.

## Base Configuration

- **Default Base URL:** `http://localhost:8000`
- **Content-Type:** `application/json` for all requests
- **CORS:** Must allow requests from `http://localhost:3000` (or your frontend URL)

---

## Endpoints

### 1. List Available Servers

Returns all available MCP servers/tools that can be connected to.

**Endpoint:** `GET /servers`

**Response:**
```json
[
  {
    "id": "server-id-1",
    "name": "Human Readable Name",
    "path": "/path/to/server/script.py",
    "description": "Optional description of what this server does"
  },
  {
    "id": "weather",
    "name": "Weather Service",
    "path": "/servers/weather/server.py",
    "description": "Get weather information for any location"
  }
]
```

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the server |
| `name` | string | Display name shown in the UI |
| `path` | string | Path to the server script (can be used internally) |

**Optional Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Brief description of the server's capabilities |
| `tools` | Tool[] | Pre-loaded list of available tools (usually populated after connection) |

---

### 2. Connect to a Server

Establishes a connection to a specific MCP server.

**Endpoint:** `POST /connect/{server_id}`

**URL Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `server_id` | string | The `id` of the server to connect to |

**Response (Success - 200):**
```json
{
  "success": true,
  "server_id": "weather",
  "server_name": "Weather Service",
  "tools": [
    {
      "name": "get_weather",
      "description": "Get current weather for a city"
    },
    {
      "name": "get_forecast",
      "description": "Get 5-day weather forecast"
    }
  ]
}
```

**Response (Error - 4xx/5xx):**
```json
{
  "detail": "Error message describing what went wrong"
}
```

**Required Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | ID of the connected server |
| `server_name` | string | Display name of the connected server |
| `tools` | Tool[] | Array of available tools on this server |

**Tool Object:**
```json
{
  "name": "tool_name",
  "description": "What this tool does"
}
```

---

### 3. Get Connection Status

Returns the current connection status.

**Endpoint:** `GET /status`

**Response (Connected):**
```json
{
  "connected": true,
  "server_id": "weather",
  "tools": [
    {
      "name": "get_weather",
      "description": "Get current weather for a city"
    }
  ]
}
```

**Response (Disconnected):**
```json
{
  "connected": false,
  "server_id": null,
  "tools": []
}
```

---

### 4. Disconnect from Server

Disconnects from the current server.

**Endpoint:** `POST /disconnect`

**Response (Success - 200):**
```json
{
  "success": true
}
```

---

### 5. Send Chat Message (Streaming) ⭐ **Primary Endpoint**

Sends a user message and streams back the response with real-time tool call updates.

**Endpoint:** `POST /chat/stream`

**Request Body:**
```json
{
  "message": "What is the weather in San Francisco?"
}
```

**Response:** Server-Sent Events (SSE) stream

**Content-Type:** `text/event-stream`

#### SSE Event Format

Each event follows the SSE format:
```
data: {json_payload}\n\n
```

#### Event Types

**1. Tool Start Event** - Emitted when a tool begins executing
```json
{
  "type": "tool_start",
  "id": "tc-1",
  "name": "get_weather",
  "args": {
    "city": "San Francisco",
    "units": "fahrenheit"
  }
}
```

**2. Tool End Event** - Emitted when a tool finishes executing
```json
{
  "type": "tool_end",
  "id": "tc-1",
  "name": "get_weather"
}
```

**3. Text Event** - Emitted for response text chunks
```json
{
  "type": "text",
  "content": "The weather in San Francisco is "
}
```

**4. Done Signal** - Indicates stream completion
```
data: [DONE]
```

**5. Error Signal** - Indicates an error occurred
```
data: [ERROR] Error message here
```

#### Complete SSE Stream Example

```
data: {"type": "tool_start", "id": "tc-1", "name": "get_weather", "args": {"city": "San Francisco"}}

data: {"type": "tool_end", "id": "tc-1", "name": "get_weather"}

data: {"type": "text", "content": "The current "}

data: {"type": "text", "content": "weather in "}

data: {"type": "text", "content": "San Francisco "}

data: {"type": "text", "content": "is 65°F and sunny."}

data: [DONE]
```

#### Event Field Reference

| Event Type | Field | Type | Required | Description |
|------------|-------|------|----------|-------------|
| `tool_start` | `type` | string | ✓ | Always `"tool_start"` |
| | `id` | string | ✓ | Unique ID for this tool call (used to match with `tool_end`) |
| | `name` | string | ✓ | Name of the tool being called |
| | `args` | object | ✓ | Arguments passed to the tool |
| `tool_end` | `type` | string | ✓ | Always `"tool_end"` |
| | `id` | string | ✓ | ID matching the corresponding `tool_start` |
| | `name` | string | ✓ | Name of the tool that finished |
| `text` | `type` | string | ✓ | Always `"text"` |
| | `content` | string | ✓ | Text chunk to append to the response |

---

### 6. Send Chat Message (Non-Streaming) - Optional

Alternative endpoint for non-streaming responses.

**Endpoint:** `POST /chat`

**Request Body:**
```json
{
  "message": "What is the weather in San Francisco?"
}
```

**Response:**
```json
{
  "response": "The current weather in San Francisco is 65°F and sunny.",
  "tool_calls": [
    {
      "name": "get_weather",
      "args": {
        "city": "San Francisco"
      },
      "result": "65°F, sunny, humidity 45%"
    }
  ]
}
```

---

## CORS Configuration

Your backend must include appropriate CORS headers. Example for FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Implementation Notes

### Tool Call Flow

1. User sends message via `POST /chat/stream`
2. Backend processes with AI model (e.g., Claude, GPT)
3. If AI decides to use a tool:
   - Emit `tool_start` event immediately
   - Execute the tool
   - Emit `tool_end` event when complete
4. Repeat step 3 for multiple tool calls
5. When AI generates final response text, emit `text` events
6. Send `[DONE]` to signal completion

### Important Behaviors

1. **Tool IDs must be unique** within a single request and must match between `tool_start` and `tool_end`

2. **Text events should only contain the final response** - Do not include intermediate reasoning like "Let me search for that..." Only send the actual answer.

3. **Text can be chunked** - Send text in small chunks (e.g., 5-10 characters) for a smooth streaming effect, or send larger chunks for faster display.

4. **Error handling** - Use `[ERROR] message` format for stream errors, or return HTTP error codes for request-level errors.

5. **Connection state** - The backend should maintain connection state. Only one server can be connected at a time.

---

## TypeScript Interface Reference

These are the exact TypeScript interfaces the frontend uses:

```typescript
export interface Server {
  id: string;
  name: string;
  path: string;
  tools?: Tool[];
}

export interface Tool {
  name: string;
  description: string;
}

export interface ConnectionStatus {
  connected: boolean;
  server_id?: string;
  tools?: Tool[];
}

export interface StreamEvent {
  type: 'tool_start' | 'tool_end' | 'text';
  id?: string;      // Required for tool_start and tool_end
  name?: string;    // Required for tool_start and tool_end
  args?: any;       // Required for tool_start
  content?: string; // Required for text
}

export interface ChatResponse {
  response: string;
  tool_calls: Array<{
    name: string;
    args: any;
    result?: string;
  }>;
}
```

---

## Quick Checklist

- [ ] `GET /servers` returns array of server objects
- [ ] `POST /connect/{id}` connects and returns tools
- [ ] `GET /status` returns connection status
- [ ] `POST /disconnect` disconnects cleanly
- [ ] `POST /chat/stream` streams SSE events
- [ ] CORS headers configured for frontend origin
- [ ] Tool IDs are unique and consistent between start/end
- [ ] Only final response text is streamed (no intermediate reasoning)

