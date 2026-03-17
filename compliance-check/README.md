# CORTEX Compliance Check - Lead Magnet

## Deployment Instructions

This is a static, zero-dependency HTML file (`index.html`) designed for maximum conversion. It functions as the entry point for the CORTEX funnel.

### 1. Local Testing
Simply open `index.html` in your browser. No build step is required.
```bash
open index.html
```

### 2. Form Integration
Search for the `submitLead()` function at the bottom of `index.html`. It currently logs the lead and the compliance scores to the console.
You need to wire this up to your lead capture system (e.g., Zapier Webhook, Mailchimp, or the CORTEX backend).

```javascript
function submitLead() {
  const email = document.getElementById('email-input').value.trim();
  // ... validation ...

  // REPLACE THIS with your actual POST request
  console.log('[CORTEX LEAD]', { email, scores: answers, timestamp: new Date().toISOString() });
  
  // ... success state ...
}
```

### 3. Production Deployment (Vercel / Netlify / Cloudflare Pages)
1. Initialize a git repository in this folder if it isn't one already.
2. Push to GitHub.
3. Import the repository in your hosting provider of choice.
4. Set the root directory to this folder. No build command is necessary.

Since there are no external dependencies other than Google Fonts, this page will load instantly.
