# Tutorial: Site Monitoring Daemon

Set up CORTEX's built-in daemon (MOSKV-1) to monitor your production sites.

## What the Daemon Does

MOSKV-1 is a background watchdog that monitors:

- 🌐 **Site uptime** — HTTP health checks with configurable intervals
- 👻 **Ghost detection** — Identifies stale or abandoned projects
- 🧠 **Memory freshness** — Alerts when CORTEX hasn't been synced recently
- 🔒 **SSL certificates** — Warns before certificate expiry
- 💾 **Disk usage** — Alerts on low storage

## Start the Daemon

```bash
# Install with CLI
pip install cortex-persist

# Start in background
moskv-daemon start

# Check status
moskv-daemon status
```

## Configure Monitoring

The daemon configuration lives at `~/.cortex/daemon.yml`:

```yaml
# Sites to monitor
sites:
  - url: https://your-production-site.com
    name: Production
    interval: 60  # seconds
    timeout: 10

  - url: https://staging.your-site.com
    name: Staging
    interval: 300

# Ghost detection
ghosts:
  stale_threshold_days: 30
  warn_threshold_days: 14

# Memory freshness
memory:
  sync_warn_hours: 24

# SSL monitoring
ssl:
  warn_days_before_expiry: 30

# Disk monitoring
disk:
  warn_threshold_percent: 90
```

## Receiving Alerts

On macOS, the daemon sends native notifications via `osascript`. You'll see alerts for:

- 🔴 **Site down** — Immediate notification when a health check fails
- 🟡 **SSL expiring** — 30 days before certificate expiry
- 👻 **Stale project** — When a project hasn't been updated in 30+ days
- 💾 **Low disk** — When disk usage exceeds 90%

## Python Integration

Use the daemon programmatically:

```python
from cortex.daemon import CortexDaemon
from cortex.engine import CortexEngine

engine = CortexEngine()
engine.init_db()

daemon = CortexDaemon(engine)
status = daemon.check_all()

if not status.all_healthy():
    print("⚠️ Issues detected:")
    for alert in status.sites:
        print(f"  🌐 {alert.name}: {alert.message}")
    for alert in status.ghost_alerts:
        print(f"  👻 {alert.project}: {alert.message}")
    for alert in status.cert_alerts:
        print(f"  🔒 {alert.domain}: {alert.message}")
```

## Integrating with CI/CD

Add a health check to your deployment pipeline:

```yaml
# .github/workflows/health.yml
name: Health Check
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install cortex-persist
      - run: |
          python -c "
          from cortex.daemon import CortexDaemon
          from cortex.engine import CortexEngine
          engine = CortexEngine()
          engine.init_db()
          d = CortexDaemon(engine)
          status = d.check_all()
          assert status.all_healthy(), 'Health check failed!'
          "
```

## Best Practices

!!! tip "Start simple"
    Begin with just site monitoring, then add ghost detection and memory freshness as your CORTEX usage grows.

!!! warning "Don't over-monitor"
    Set reasonable intervals. 60 seconds for production, 5 minutes for staging. More frequent checks don't add value but increase resource usage.
