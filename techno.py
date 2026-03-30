import re

css_path = "/Users/borjafernandezangulo/10_PROJECTS/web/borjamoskv_site/style.css"

try:
    with open(css_path) as f:
        content = f.read()

    # Eradicate pure white
    content = content.replace("#FFFFFF", "#E0E0E0")
    content = content.replace("#ffffff", "#e0e0e0")
    content = re.sub(r'#fff\b', '#e0e0e0', content, flags=re.IGNORECASE)

    # Replace 'color: white' and 'background: white'
    content = re.sub(r'color:\s*white\b', 'color: #e0e0e0', content, flags=re.IGNORECASE)
    content = re.sub(r'background:\s*white\b', 'background: #020202', content, flags=re.IGNORECASE)
    content = re.sub(r'background-color:\s*white\b', 'background-color: #020202', content, flags=re.IGNORECASE)

    # Convert rgba(255, 255, 255, X) to rgba(220, 220, 220, X) to dim bright transparencies
    content = content.replace("rgba(255, 255, 255,", "rgba(220, 220, 220,")
    content = content.replace("rgba(255,255,255,", "rgba(220, 220, 220,")

    # Shift :root to TECHNO NOIR if needed
    content = content.replace("--bg-color: #050505;", "--bg-color: #000000;")
    content = content.replace("--text-main: #FFFFFF;", "--text-main: #E0E0E0;")

    with open(css_path, "w") as f:
        f.write(content)

    print("SUCCESS: TECHNO NOIR PROTOCOL ENFORCED")
except Exception as e:
    print(f"FAILED: {e}")
