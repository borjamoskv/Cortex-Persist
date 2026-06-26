import os

def patch_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

patch_file('cortex/cli/dashboard_cmds.py', [
    ('time.sleep(interval)', 'time.sleep(interval)  # noqa: TID251 # Synchronous CLI loop')
])

patch_file('cortex/cli/health_cmds.py', [
    ('time.sleep(interval)', 'time.sleep(interval)  # noqa: TID251 # Synchronous CLI loop')
])

patch_file('cortex/cli/reactor.py', [
    ('time.sleep(0.2)', 'time.sleep(0.2)  # noqa: TID251 # Synchronous UI loop')
])

patch_file('cortex/mcp/apollo_tools.py', [
    ('time.sleep(1)  # Rate limit respect', 'time.sleep(1)  # noqa: TID251 # Synchronous rate limiting')
])

patch_file('cortex/observability/exergy_engine.py', [
    ('time.sleep(1)  # Fake run', 'time.sleep(1)  # noqa: TID251 # Synchronous fake run delay'),
    ('time.sleep(2)', 'time.sleep(2)  # noqa: TID251 # Synchronous simulation delay')
])

patch_file('cortex/production/chaos_v2.py', [
    ('time.sleep(random.expovariate(0.001))', 'time.sleep(random.expovariate(0.001))  # noqa: TID251 # Synchronous chaos delay')
])

print('Patched time.sleep successfully.')
