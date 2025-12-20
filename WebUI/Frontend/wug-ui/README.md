# WhatsUp Gold Automation Console - Frontend

React-based web interface for the WhatsUp Gold Automation Console.

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

```bash
npm install
```

### Development

```bash
npm start
```

Runs the app in development mode. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### Build for Production

```bash
npm run build
```

Builds the app for production to the `build` folder.

## Features

- Modern dark theme UI
- Credential management with localStorage
- Excel-like grid for report scheduling
- Full-width log/config viewing with word wrapping
- File rename and download capabilities
- Responsive design

## Project Structure

```
src/
├── components/          # Reusable components
│   └── CredentialsSelector.jsx
├── utils/              # Utility functions
│   └── credentials.js
├── App.jsx             # Main app component
├── BulkChanges.jsx     # Bulk operations page
├── RouterCommands.jsx  # Router commands page
├── History.jsx         # History page
├── ConfigBackups.jsx   # Config backups page
├── ReportSchedule.jsx # Report schedule page
├── CredentialsManager.jsx # Credentials management
└── index.css          # Global styles
```

## Environment Variables

The frontend expects the backend API to be running at `http://localhost:8000`. To change this, update the fetch URLs in the components or use environment variables.
