# Teams App Package

This folder contains the Microsoft Teams app manifest for the Expense Bot.

## Setup Instructions

### 1. Update the manifest

Edit `manifest.json` and replace `{{APP_ID}}` with your actual Azure Bot App ID (the GUID you got when creating the Azure Bot).

### 2. Add icon files

You need two PNG icon files:
- `icon-color.png` - 192x192 pixels, full color icon
- `icon-outline.png` - 32x32 pixels, outline/monochrome icon

For quick testing, you can use any placeholder images of the correct sizes.

### 3. Create the app package

Zip the contents of this folder (manifest.json + both icons):

```bash
cd teams_app
zip -r ../expense-bot.zip manifest.json icon-color.png icon-outline.png
```

### 4. Sideload in Teams

1. Open Microsoft Teams
2. Click "Apps" in the left sidebar
3. Click "Manage your apps" at the bottom
4. Click "Upload an app"
5. Choose "Upload a custom app" 
6. Select the `expense-bot.zip` file

### 5. Start chatting!

Find "Expense Bot" in your apps and start a personal chat. Send a receipt photo with a caption to parse it.

## Troubleshooting

- **Bot not responding**: Check that your Azure Function is deployed and the messaging endpoint is configured correctly in Azure Bot
- **Image download fails**: Ensure the bot has proper permissions and the App ID/Secret are correct
- **Parsing errors**: Check Azure Function logs in the Azure Portal



