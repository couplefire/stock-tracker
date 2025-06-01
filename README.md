# Stock Availability Tracker

A lightweight web-based system for tracking item availability across e-commerce websites. The system automatically checks items periodically and sends email notifications when availability changes.

## Features

- 🔍 **Automated Stock Checking**: Uses Selenium with headless browser to check websites every 10 seconds
- 📧 **Email Notifications**: Sends alerts when item availability changes
- 🎯 **Pattern-Based Detection**: Define custom regex patterns to detect out-of-stock status
- 🌐 **Modern Web Interface**: Clean, responsive UI for managing tracked items and email notifications
- 💾 **Lightweight Storage**: Uses SQLite database for minimal resource usage
- 🚀 **Optimized for Low Resources**: Designed to run on 1GB RAM / 1 CPU core

## Screenshots

The web interface provides:
- Real-time status of all tracked items
- Easy management of tracking rules
- Email notification settings
- Manual check triggers

## Prerequisites

- Python 3.8+
- Chrome or Firefox browser installed (for Selenium)
- ChromeDriver or GeckoDriver in PATH

## Installation

1. Clone the repository:
```bash
cd stock-tracker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install ChromeDriver (for Chrome):
```bash
# On macOS with Homebrew:
brew install chromedriver

# On Ubuntu/Debian:
sudo apt-get install chromium-chromedriver

# Or download manually from: https://chromedriver.chromium.org/
```

5. Configure environment (optional for email notifications):
```bash
cp env.example .env
# Edit .env with your SMTP settings
```

## Configuration

### Email Setup (Optional)

To enable email notifications, configure SMTP settings in `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

For Gmail, you'll need to:
1. Enable 2-factor authentication
2. Generate an app-specific password: https://myaccount.google.com/apppasswords

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. The stock tracker will start automatically and check items every 10 seconds.

## Usage Guide

### Adding Items to Track

1. Click "Add Item" in the web interface
2. Fill in the required fields:
   - **Item Name**: A descriptive name for the item
   - **Item URL**: The full URL of the product page
   - **Pattern to Match**: A regex pattern to search for (e.g., `out of stock|unavailable|sold out`)
   - **Match Count**: If the pattern matches this many times or more, the item is considered out of stock

### Understanding Rules

The tracking rule logic works as follows:
- The system searches the webpage for your pattern using regex
- If the pattern is found **at least** the specified number of times, the item is marked as **out of stock**
- Otherwise, the item is marked as **available**

Example patterns:
- `out of stock` - Simple text match
- `out of stock|unavailable` - Match either phrase
- `(out of|no) stock` - More complex pattern
- `stock.*0` - Match "stock" followed by "0"

### Managing Email Notifications

1. Click "Add Email" to add notification recipients
2. All added emails will receive alerts when any item's availability changes
3. Emails include the item name, new status, and a direct link to the product

## System Architecture

- **Flask Web Server**: Serves the web interface and REST API
- **SQLite Database**: Stores items, rules, emails, and availability history
- **Selenium Scrapers**: Headless browser instances that check websites
- **Background Tracker**: Threading-based scheduler that coordinates checks
- **Email Notifier**: SMTP client for sending notifications

## Resource Optimization

The system is optimized for low-resource environments:
- Headless browser with minimal features enabled
- Images and unnecessary content disabled during scraping
- Efficient SQLite database with connection pooling
- Lightweight web interface without heavy frameworks
- Smart threading to prevent concurrent checks of the same item

## API Endpoints

- `GET /api/items` - List all tracked items
- `POST /api/items` - Add a new item
- `PUT /api/items/{id}` - Update an item
- `DELETE /api/items/{id}` - Delete an item
- `POST /api/items/{id}/check` - Force check an item
- `GET /api/emails` - List notification emails
- `POST /api/emails` - Add an email
- `DELETE /api/emails/{id}` - Remove an email
- `GET /api/tracker/status` - Get tracker status

## Troubleshooting

### Selenium Issues
- Ensure ChromeDriver/GeckoDriver is installed and in PATH
- Check that Chrome/Firefox browser is installed
- Try switching between Chrome and Firefox if one doesn't work

### High Memory Usage
- Reduce check frequency in `app.py` (change `check_interval`)
- Limit the number of items being tracked
- Ensure you're using headless mode

### Email Not Working
- Verify SMTP credentials in `.env`
- Check firewall settings for SMTP port
- For Gmail, ensure app-specific password is used

## Development

To run in development mode with auto-reload:
```bash
export FLASK_ENV=development
python app.py
```

## License

MIT License - feel free to use and modify as needed. 