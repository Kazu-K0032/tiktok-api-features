# TikTok API Features

[日本語](../../README.md) | English

An application that retrieves and displays user profile information and posted videos using the TikTok API.

## UI Introduction (2025.08.05)

### Login Screen (/)

<img src="../images/login1.png" width="45%" />

### Dashboard (/dashboard)

<div style="display: flex; column-gap:8px;">
    <img src="../images/dashboard_1.png" width="45%" />
    <img src="../images/dashboard_2.png" width="45%" />
</div>

### Upload (/upload)

<div style="display: flex; gap:8px; flex-wrap: wrap;">
    <img src="../images/upload_1.png" width="45%" />
    <img src="../images/upload_2.png" width="45%" />
    <img src="../images/upload_3.png" width="45%" />
</div>

## Features

### Authentication & User Management

- **TikTok OAuth 2.0 Authentication (PKCE method)**
- **Multi-user Support**: Simultaneous management of multiple accounts
- **User Switching Function**: Easy account switching from header
- **Session Management**: Automatic access token renewal and expiration management

### Profile & Statistics Information

- **User Profile Information Retrieval & Display**
  - Avatar image, display name, username
  - Bio description, verified account display
  - Direct link to profile page
- **Detailed Statistics Display**
  - Following count, follower count, likes count, video count
  - Total view count, total share count, average engagement rate

### Video Management & Analysis

- **Posted Video List Retrieval & Display**
  - Thumbnail image card display
  - Pagination functionality (6 items per page)
  - Video ID, posting date, statistics display
- **Video Detail Information Display**
  - Duration, resolution, engagement rate
  - View count, like count, comment count, share count
  - Video viewing via TikTok embed link

### Video Upload Functionality

- **TikTok Content Posting API Support**
  - **Direct Post**: Immediate posting to TikTok
  - **Draft Post**: Posting possible later via TikTok app
- **Posting Configuration Options**
  - Caption (maximum 2200 characters, hashtag support)
  - Privacy settings (unaudited apps limited to "Self Only")
  - Comment, duet, stitch disable settings
- **File Management**
  - Video file size limit (maximum 100MB)
  - Supported formats: MP4, AVI, MOV, WMV
  - File information preview
- **Posting Restriction Handling**
  - 5-minute posting interval restriction
  - Automatic spam prevention error detection
  - Private account requirement verification

## Setup Instructions

### Sandbox Configuration

Reference site: [How to Create TikTok for Developers Account](https://nfr-log.com/how-to_create_tiktokfordevelopers/#index_id2)

After adding an account and accessing the portal settings screen, configure the Sandbox environment as follows:

<div style="display: flex; gap:8px; flex-wrap: wrap;">
    <img src="../images/sandbox_1.png" width="45%" />
    <img src="../images/sandbox_2.png" width="45%" />
    <img src="../images/sandbox_3.png" width="45%" />
    <img src="../images/sandbox_4.png" width="45%" />
    <img src="../images/sandbox_5.png" width="45%" />
    <img src="../images/sandbox_6.png" width="45%" />
    <img src="../images/sandbox_7.png" width="45%" />
    <img src="../images/sandbox_8.png" width="45%" />
    <img src="../images/sandbox_9.png" width="45%" />
</div>

### Repository Setup

#### 1. Clone the Repository

```bash
git clone git@github.com:Kazu-K0032/TikTok-API-Features.git
cd tiktok-api-features
```

#### 2. Create and Activate Virtual Environment

```bash
# Linux (if needed)
sudo apt update && sudo apt install -y python3.12-venv

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

```bash
# Create .env file
cp env.example .env
```

#### 5. Run the Application

```bash
python main.py
```

#### 6. Access via Browser

```
http://localhost:3456
```

#### Notes

- Python 3.8 or higher is required
- TikTok for Developers account and app configuration is required
- Environment variable configuration is mandatory (see "Sandbox Configuration" for details)
