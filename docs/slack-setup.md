# Slack Integration Setup Guide

This guide walks you through setting up the Slack integration for the Tenant Access Request Service.

## Prerequisites

- Admin access to your Slack workspace
- The tenant-access-request-service deployed and accessible via HTTPS (Slack requires HTTPS for callbacks)

---

## Step 1: Create a Slack Channel

1. Open Slack and go to your workspace
2. Click the **+** button next to "Channels" in the sidebar
3. Select **Create a channel**
4. Name it `#berdl-governance` (or your preferred name)
5. Set it to **Private** if you want only admins to see requests
6. Click **Create**
7. **Note the channel**: You'll add the bot here later

---

## Step 2: Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Enter:
   - **App Name**: `BERDL Access Requests`
   - **Workspace**: Select your workspace
5. Click **Create App**

---

## Step 3: Configure Bot Token Scopes

The bot needs permissions to post and update messages.

1. In your app settings, go to **OAuth & Permissions** (left sidebar)
2. Scroll down to **Scopes** → **Bot Token Scopes**
3. Click **Add an OAuth Scope** and add:
   - `chat:write` - Send messages
   - `chat:write.public` - Post to public channels without joining (optional)

![Bot Token Scopes](https://api.slack.com/img/api/permissions-add-scopes.png)

---

## Step 4: Install App to Workspace

1. Still in **OAuth & Permissions**, scroll to the top
2. Click **Install to Workspace**
3. Review the permissions and click **Allow**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)
   - This is your `SLACK_BOT_TOKEN`

---

## Step 5: Get the Signing Secret

The signing secret verifies that requests come from Slack.

1. Go to **Basic Information** (left sidebar)
2. Scroll down to **App Credentials**
3. **Copy the Signing Secret**
   - This is your `SLACK_SIGNING_SECRET`

---

## Step 6: Enable Interactivity

This allows Slack to call your service when users click Approve/Deny buttons.

1. Go to **Interactivity & Shortcuts** (left sidebar)
2. Toggle **Interactivity** to **On**
3. Enter your **Request URL**:
   ```
   https://your-service-domain.com/slack/interact
   ```
   > **Note**: This must be HTTPS. For local development, use ngrok or similar.
4. Click **Save Changes**

### For Local Development (using ngrok)

If testing locally, you can use [ngrok](https://ngrok.com/) to expose your local service:

```bash
# Start your service on port 8000
docker-compose up

# In another terminal, start ngrok
ngrok http 8000
```

Use the ngrok HTTPS URL as your Request URL:
```
https://abc123.ngrok-free.dev/slack/interact
```

---

## Step 7: Get the Channel ID

1. Open Slack and go to your `#berdl-governance` channel
2. Click the channel name at the top to open channel details
3. Scroll down - the **Channel ID** is at the bottom (starts with `C`)
   - This is your `SLACK_CHANNEL_ID`

**Alternative method:**
- Right-click the channel → **Copy link**
- The URL will be like: `https://workspace.slack.com/archives/C0123456789`
- The `C0123456789` part is your Channel ID

---

## Step 8: Invite Bot to Channel

1. Go to your `#berdl-governance` channel
2. Type `/invite @BERDL Access Requests` (or whatever you named your app)
3. Press Enter to invite the bot

---

## Step 9: Configure Environment Variables

Add these to your `.env` file:

```bash
# From Step 4
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# From Step 5
SLACK_SIGNING_SECRET=your-signing-secret-here

# From Step 7
SLACK_CHANNEL_ID=C0123456789
```

---

## Step 10: Test the Integration

1. Start the service:
   ```bash
   docker-compose up
   ```

2. Make a test request:
   ```bash
   curl -X POST http://localhost:8000/requests \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_KBASE_TOKEN" \
     -d '{
       "tenant_name": "test-tenant",
       "permission": "read_only",
       "justification": "Testing Slack integration"
     }'
   ```

3. Check the `#berdl-governance` channel - you should see a message with Approve/Deny buttons!

---

## Troubleshooting

### "channel_not_found" Error
- Make sure the bot is invited to the channel
- Verify the Channel ID is correct

### "invalid_auth" Error
- Check that `SLACK_BOT_TOKEN` is correct and starts with `xoxb-`
- Verify the app is still installed to your workspace

### "request_url_verification_failed" Error
- Ensure your service is accessible via HTTPS
- Check that the `/slack/interact` endpoint is working

### Buttons Not Working
- Verify Interactivity is enabled in your Slack app settings
- Check that the Request URL is correct and accessible
- Look at your service logs for signature verification errors

---

## Summary of Environment Variables

| Variable | Example | Where to Find |
|----------|---------|---------------|
| `SLACK_BOT_TOKEN` | `xoxb-123-456-abc` | OAuth & Permissions page |
| `SLACK_SIGNING_SECRET` | `abc123def456` | Basic Information → App Credentials |
| `SLACK_CHANNEL_ID` | `C0123456789` | Channel details or URL |

---

## Approval Flow

When a user submits a request, the bot posts a message like this:

```
🔔 Tenant Access Request

Requester: @jdoe
Tenant: kbase
Permission: read_only
Justification: Need access for data analysis

[ Approve ✓ ]  [ Deny ✗ ]
```

### Approval Process

1. **Admin clicks "Approve"** → A modal dialog opens asking for their KBase token
2. **Admin enters their token** → Token is used once to add the user to the MinIO group (not stored)
3. **Modal closes** → The original message updates to show "✅ Approved by @admin"

### Denial Process

1. **Admin clicks "Deny"** → The message immediately updates to show "❌ Denied by @admin"

