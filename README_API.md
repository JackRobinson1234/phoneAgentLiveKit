# Health Agent REST API

A REST API wrapper for the Health Agent that allows external applications to interact with the appointment scheduling system via HTTP requests.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the API server:**
   ```bash
   python api.py
   ```

3. **Test the API:**
   ```bash
   python example_api_usage.py
   ```

## API Endpoints

### Start New Conversation
```http
POST /conversations
```

**Response:**
```json
{
  "conversation_id": "uuid-string",
  "message": "Hello! I'm HealthBot...",
  "status": "started"
}
```

### Send Message
```http
POST /conversations/{conversation_id}/messages
Content-Type: application/json

{
  "message": "I need an eye doctor"
}
```

**Response:**
```json
{
  "conversation_id": "uuid-string",
  "message": "I'll help you schedule an appointment...",
  "current_state": "COLLECT_PATIENT_INFO",
  "context": {
    "patient_name": "John Smith",
    "specialty": "ophthalmology",
    "turn_count": 3
  }
}
```

### Get Conversation Status
```http
GET /conversations/{conversation_id}
```

**Response:**
```json
{
  "conversation_id": "uuid-string",
  "current_state": "COLLECT_DATE_TIME",
  "is_complete": false,
  "context": {
    "patient_name": "John Smith",
    "patient_contact": "john@email.com",
    "specialty": "ophthalmology",
    "appointment_type": "consultation",
    "turn_count": 5
  }
}
```

### List All Conversations
```http
GET /conversations
```

### End Conversation
```http
DELETE /conversations/{conversation_id}
```

### Health Check
```http
GET /health
```

## Example Usage

### cURL Examples

**Start conversation:**
```bash
curl -X POST http://localhost:5000/conversations
```

**Send message:**
```bash
curl -X POST http://localhost:5000/conversations/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a cardiologist"}'
```

### Python Example
```python
import requests

# Start conversation
response = requests.post("http://localhost:5000/conversations")
conversation_id = response.json()["conversation_id"]

# Send message
response = requests.post(
    f"http://localhost:5000/conversations/{conversation_id}/messages",
    json={"message": "I need an eye doctor"}
)

print(response.json()["message"])
```

### JavaScript Example
```javascript
// Start conversation
const startResponse = await fetch('http://localhost:5000/conversations', {
  method: 'POST'
});
const { conversation_id } = await startResponse.json();

// Send message
const messageResponse = await fetch(`http://localhost:5000/conversations/${conversation_id}/messages`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'I need a dentist appointment' })
});

const data = await messageResponse.json();
console.log(data.message);
```

## Conversation Flow

1. **POST /conversations** - Start new conversation
2. **POST /conversations/{id}/messages** - Send user messages
3. **GET /conversations/{id}** - Check status anytime
4. **DELETE /conversations/{id}** - Clean up when done

## Error Handling

The API returns standard HTTP status codes:
- `200` - Success
- `201` - Created (new conversation)
- `400` - Bad Request (invalid JSON/missing fields)
- `404` - Not Found (conversation doesn't exist)
- `500` - Internal Server Error

Error responses include details:
```json
{
  "error": "Conversation not found",
  "details": "Additional error information"
}
```

## Production Considerations

- **Session Storage**: Currently uses in-memory storage. For production, use Redis or a database
- **Authentication**: Add API keys or OAuth for security
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Logging**: Configure proper logging for monitoring
- **HTTPS**: Use HTTPS in production
- **Load Balancing**: Use multiple instances behind a load balancer

## Development

Run with debug mode:
```bash
python api.py
```

The server runs on `http://localhost:5000` by default.
