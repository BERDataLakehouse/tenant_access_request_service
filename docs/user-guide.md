# Tenant Access Request - User & Admin Guide

This guide explains how to request and approve access to tenant groups in BERDL.

---

## For Users: Requesting Access

### Step 1: Make a Request

From your JupyterHub notebook, call the `request_tenant_access()` function:

```python
from berdl_notebook_utils.minio_governance.operations import request_tenant_access

# Request read-only access
request_tenant_access(
    tenant_name="kbase",
    permission="read_only",
    justification="Need access for data analysis project"  # optional
)

# Request read-write access
request_tenant_access(
    tenant_name="kbase",
    permission="read_write",
    justification="Need to update shared datasets"
)
```

### Step 2: Wait for Approval

Your request is sent to the `#berdl-governance` Slack channel where admins can review it.

You'll see a message like:
```
✅ Request submitted successfully!
An admin will review your request in Slack.
```

### Step 3: Access Granted

Once approved, you'll have access to the tenant's data. The permissions take effect immediately.

---

## For Admins: Reviewing Requests

### Viewing Requests

Requests appear in the `#berdl-governance` Slack channel:

```
🔔 Tenant Access Request

Requester: @jdoe
Tenant: kbase
Permission: read_only
Justification: Need access for data analysis project

[ Approve ✓ ]  [ Deny ✗ ]
```

### Approving a Request

1. **Click the "Approve" button** in the Slack message
2. **A modal dialog opens** asking for your KBase token
3. **Paste your token** (from your KBase session)
4. **Click "Approve"** in the modal

The user is immediately added to the tenant group, and the Slack message updates to:

```
✅ Tenant Access Approved

Requester: @jdoe
Tenant: kbase
Permission: Read Only

Approved by @admin at 2024-12-10 21:15 UTC
```

> **Security Note**: Your token is used once to perform the action and is never stored.

### Denying a Request

1. **Click the "Deny" button** in the Slack message
2. The message immediately updates to show the denial

No further action is needed.

### Troubleshooting Approvals

**"Approval failed" error in modal:**
- Your KBase token may have expired - get a fresh token and try again
- The tenant group may not exist - check with the tenant owner
- Network issues - try again in a moment

---

## Permission Levels

| Permission | Description |
|------------|-------------|
| `read_only` | Read access to tenant data (view, download) |
| `read_write` | Full access (read, write, modify, delete) |

---
