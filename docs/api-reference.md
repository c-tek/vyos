# 📡 VyOS API Reference Overview

**Version**: 0.2.0  
**Documentation Type**: High-level API overview  
**Target Audience**: Developers, integrators, system architects

---

## 📍 **Quick Navigation**

This file provides a high-level overview of the VyOS API structure. For detailed endpoint documentation, see:

### **📖 Detailed API Documentation**
- **[Complete API Reference](user/api-reference.md)** - Comprehensive endpoint documentation
- **[Enhanced API Reference](user/api-reference-enhanced.md)** - Extended examples and use cases
- **[Interactive API Documentation](http://localhost:8001/docs)** - Live Swagger/OpenAPI interface

### **🎯 Quick Access**
- **Authentication**: [Security Guide](user/security.md#authentication)
- **Examples**: [User Examples](user/EXAMPLES.md)
- **Tutorials**: [Step-by-step Guides](user/tutorials.md)

---

## 🏗️ **API Architecture Overview**

### **Base Information**
- **Base URL**: `https://your-vyos-api.com/v1/`
- **API Version**: v1 (current), v2 (planned)
- **Data Format**: JSON (request/response)
- **Authentication**: JWT Bearer tokens
- **Rate Limiting**: Configurable per endpoint

### **Core Endpoints Categories**

#### **🔐 Authentication & Users**
```
POST   /v1/auth/token          # Obtain JWT token
GET    /v1/auth/me             # Get current user info
POST   /v1/auth/refresh        # Refresh JWT token
POST   /v1/users/              # Create user
GET    /v1/users/              # List users
```

#### **🌐 Network Management**
```
GET    /v1/subnets/            # List subnets
POST   /v1/subnets/            # Create subnet
PUT    /v1/subnets/{id}        # Update subnet
DELETE /v1/subnets/{id}        # Delete subnet

GET    /v1/static-dhcp/        # List DHCP assignments
POST   /v1/static-dhcp/        # Create DHCP assignment
```

#### **🔧 Configuration & Operations**
```
GET    /v1/port-mappings/      # List port mappings
POST   /v1/port-mappings/      # Create port mapping

GET    /v1/bulk/operations/    # List bulk operations
POST   /v1/bulk/execute        # Execute bulk operation
```

#### **📊 Analytics & Monitoring**
```
GET    /v1/analytics/metrics   # Get performance metrics
GET    /v1/analytics/traffic   # Get traffic statistics
GET    /v1/topology/           # Get network topology
```

#### **🛡️ Security & Audit**
```
GET    /v1/rbac/roles          # List roles
POST   /v1/rbac/roles          # Create role
GET    /v1/audit/logs          # Access audit logs
```

---

## 🔗 **API Response Patterns**

### **Standard Response Format**
```json
{
  "status": "success|error",
  "data": {...},
  "message": "Human readable message",
  "timestamp": "2025-06-18T10:30:00Z",
  "request_id": "uuid-string"
}
```

### **Error Response Format**
```json
{
  "error": {
    "type": "ValidationError",
    "code": 422,
    "message": "Invalid input data",
    "details": {...},
    "path": "/v1/subnets/"
  }
}
```

---

## 🔐 **Authentication Overview**

### **JWT Token Authentication**
```bash
# 1. Obtain token
curl -X POST http://localhost:8001/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Use token in requests
curl -X GET http://localhost:8001/v1/subnets/ \
  -H "Authorization: Bearer <your-jwt-token>"
```

---

**📡 For complete documentation, see [user/api-reference.md](user/api-reference.md)**
